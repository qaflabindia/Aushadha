"""Build help-centre.html from content.json and template.html.

Run from anywhere:  python3 backend/help/build_help.py

content.json holds the structure and the original text: sections, topics, steps, pictures
and tips. Every piece of text gets a stable data-edit-id built from the section and topic
ids, so admin edits (saved separately, see src/routers/help_router.py) still match after a
rebuild. Change an id only if you mean to drop the admin edits for that text.

content.json shape:
{
  "version": "1.0",
  "hero": {"eyebrow": "...", "title": "...", "text": "..."},
  "sections": [
    {"id": "getting-started", "icon": "start|home|upload|chat|graph|settings|admin|tour|trouble|book",
     "title": "...", "summary": "...", "audience": "all|staff|admin",
     "topics": [
       {"id": "sign-in", "title": "...", "body": "...", "steps": ["...", "..."],
        "image": "/help/login.png", "caption": "...", "tip": "...", "audience": "all|staff|admin",
        "images": [{"src": "/help/a.png", "caption": "..."}],  (more pictures, optional)
        "contact": true}
     ...
     ]}
  ],
  "footer": "...",
  "footer_contact": true
}
"contact": true adds the support email link (HELP_SUPPORT_EMAIL on the backend) to a topic;
"footer_contact" adds it to the footer.
audience: all = everyone (default), staff = doctors and admins, admin = admins only. Hiding is
for clarity, not security: the help text is not secret.
Pictures are served by the frontend from frontend/public/help/.
Deep links: a topic's anchor is "<section id>-<topic id>" (e.g. settings-vault); the app opens
one with openHelp('settings-vault') from src/components/Help/helpLinks.ts.
Bump "version" when the content changes in a release; the build date is stamped automatically.
"""
import json
import re
from datetime import date
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Filled in by the backend from HELP_SUPPORT_EMAIL; removed when that is not set
CONTACT = (
    '<a class="support-link" href="mailto:{{SUPPORT_EMAIL}}"><svg><use href="#i-mail"/></svg>'
    "<span>{{SUPPORT_EMAIL}}</span></a>"
)
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
ICONS = {"start", "home", "upload", "chat", "graph", "settings", "admin", "tour", "trouble", "book", "research"}
# Who sees a section or topic. Admins and the standalone file see everything.
AUDIENCES = {"all": "", "staff": "Doctors & admins", "admin": "Admins"}


def audience(item: dict, where: str) -> str:
    a = item.get("audience", "all")
    if a not in AUDIENCES:
        raise SystemExit(f"Unknown audience {a!r} in {where}: use all, staff or admin")
    return a


def text(tag: str, edit_id: str, value: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-edit-id="{edit_id}">{escape(value)}</{tag}>'


def build() -> str:
    content = json.loads((HERE / "content.json").read_text(encoding="utf-8"))
    template = (HERE / "template.html").read_text(encoding="utf-8")
    seen = set()

    def check(i: str) -> str:
        if not ID.match(i):
            raise SystemExit(f"Bad id {i!r}: use lowercase letters, digits and dashes")
        if i in seen:
            raise SystemExit(f"Duplicate id {i!r}")
        seen.add(i)
        return i

    nav, body = [], []
    hero = content.get("hero", {})
    chips = "".join(
        f'<button class="chip" type="button" data-go="{s["id"]}" data-audience="{audience(s, s["id"])}">'
        f'<span class="nl">{escape(s["title"])}</span></button>'
        for s in content["sections"]
    )
    built = date.today()
    stamp = (
        f'<div class="meta-line">Version {escape(str(content.get("version", "1.0")))} · Updated '
        f'<span id="updated" data-built="{built.isoformat()}">{built.strftime("%-d %b %Y")}</span></div>'
    )
    body.append(
        '<div class="hero">'
        + text("div", "hero-eyebrow", hero.get("eyebrow", "Aushadha"), "eyebrow")
        + text("h1", "hero-title", hero.get("title", "Help Centre"))
        + text("p", "hero-text", hero.get("text", ""))
        + f'<div class="chips">{chips}</div>{stamp}</div>'
    )

    for sec in content["sections"]:
        sid = check(sec["id"])
        icon = sec.get("icon", "home")
        if icon not in ICONS:
            raise SystemExit(f"Unknown icon {icon!r} in section {sid}")
        aud = audience(sec, sid)
        nav.append(
            f'<button class="navlink" type="button" data-go="{sid}" data-audience="{aud}"><svg><use href="#i-{icon}"/></svg>'
            f'<span class="nl">{escape(sec["title"])}</span></button>'
        )
        badge = f'<span class="badge">{AUDIENCES[aud]}</span>' if AUDIENCES[aud] else ""
        parts = [
            f'<section class="sec" id="{sid}" data-audience="{aud}"><div class="sec-head"><div class="sec-icon"><svg><use href="#i-{icon}"/></svg></div><div>',
            f'<h2><span data-edit-id="{sid}-title">{escape(sec["title"])}</span>{badge}</h2>',
            text("p", f"{sid}-summary", sec.get("summary", ""), "summary"),
            "</div></div>",
        ]
        for top in sec.get("topics", []):
            tid = f"{sid}-{check(sid + '-' + top['id'])[len(sid) + 1:]}"
            taud = audience(top, tid)
            tbadge = f'<span class="badge">{AUDIENCES[taud]}</span>' if AUDIENCES[taud] and taud != aud else ""
            parts.append(f'<details class="topic" id="{tid}" data-audience="{taud}"><summary>')
            parts.append(text("span", f"{tid}-title", top["title"]) + tbadge)
            parts.append('<svg class="chev"><use href="#i-chev"/></svg></summary><div class="topic-body">')
            if top.get("body"):
                parts.append(text("p", f"{tid}-body", top["body"]))
            if top.get("steps"):
                parts.append('<ol class="steps">')
                for n, step in enumerate(top["steps"], 1):
                    parts.append(text("li", f"{tid}-step-{n}", step))
                parts.append("</ol>")
            pictures = list(top.get("images", []))
            if top.get("image"):
                pictures.insert(0, {"src": top["image"], "caption": top.get("caption", "")})
            for n, pic in enumerate(pictures, 1):
                alt = escape(pic.get("caption") or top["title"])
                cap_id = f"{tid}-caption" if n == 1 else f"{tid}-caption-{n}"
                parts.append(f'<figure><img src="{escape(pic["src"].lstrip("/"))}" alt="{alt}" loading="lazy">')
                if pic.get("caption"):
                    parts.append(text("figcaption", cap_id, pic["caption"]))
                parts.append("</figure>")
            if top.get("contact"):
                parts.append(CONTACT)
            if top.get("tip"):
                parts.append('<div class="tip"><strong>Tip</strong>' + text("span", f"{tid}-tip", top["tip"]) + "</div>")
            parts.append("</div></details>")
        parts.append("</section>")
        body.append("".join(parts))

    if content.get("footer"):
        contact = CONTACT if content.get("footer_contact") else ""
        body.append('<footer class="foot">' + text("p", "footer-text", content["footer"]) + contact + "</footer>")
    out = template.replace("<!--NAV-->", "\n".join(nav)).replace("<!--CONTENT-->", "\n".join(body))
    if "<!--NAV-->" in out or "<!--CONTENT-->" in out or 'id="help-edits"' not in out:
        raise SystemExit("Template placeholders not filled")
    return out


if __name__ == "__main__":
    html = build()
    (HERE / "help-centre.html").write_text(html, encoding="utf-8")
    print(f"Wrote {HERE / 'help-centre.html'} ({len(html) // 1024} KB)")
