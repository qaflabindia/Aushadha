"""Help Centre: one self-contained HTML document, editable by admins, with an audit trail.

The document ships at backend/help/help-centre.html. Every text section an admin may edit
carries a `data-edit-id` attribute. Admin edits are not separate records: they are written
into the same HTML document, in its JSON block

    <script type="application/json" id="help-edits">{"edits": {...}, "audit": [...]}</script>

which the document's own script applies on load (as plain text, never as HTML). The edited
document is saved at backend/help_data/help-centre.html (git-ignored, so deploys that reset
the code keep the edits). When serving, the structure comes from the shipped file and the
edits block from the saved copy, so content updates in a deploy appear straight away. Delete
the saved copy to drop all edits.

The same block also keeps reader feedback ("Was the Help Centre helpful?", asked when the
window is closed). Only admins receive the audit trail and the feedback.

Support contact: the document shows HELP_SUPPORT_EMAIL (backend environment) wherever it
says {{SUPPORT_EMAIL}}. It is filled in when serving, so the address is not in the code.
Unset, the contact link is left out and the text falls back to "your administrator".

Routes:
  GET  /help/document  any signed-in user; non-admins get the edits and the time of the
                       last edit, but not the audit trail or the feedback
  POST /help/edit      admin only; {"section_id", "text"} replaces one section's text
  POST /help/reset     admin only; {"section_id"} restores the shipped text
  POST /help/feedback  any signed-in user; {"helpful": true|false, "comment": "..."}
"""
import json
import logging
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import User
from src.routers.admin_router import require_admin
from src.shared.google_auth import AuthenticatedUser, require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/help", tags=["Help Centre"])

_BACKEND_DIR = Path(__file__).resolve().parents[2]
SHIPPED_DOC = _BACKEND_DIR / "help" / "help-centre.html"
EDITED_DOC = Path(os.getenv("HELP_DOC_PATH", str(_BACKEND_DIR / "help_data" / "help-centre.html")))

MAX_TEXT = 4000  # characters per section
MAX_AUDIT = 1000  # oldest entries are dropped beyond this
MAX_FEEDBACK = 2000
MAX_COMMENT = 1000
_EMAIL = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[A-Za-z]{2,}$")

_EDITS_BLOCK = re.compile(
    r'(<script type="application/json" id="help-edits">)(.*?)(</script>)', re.DOTALL
)
_SECTION_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
_lock = threading.Lock()


class EditRequest(BaseModel):
    section_id: str
    text: str


class ResetRequest(BaseModel):
    section_id: str


class FeedbackRequest(BaseModel):
    helpful: bool
    comment: str = ""


def _read_document() -> str:
    """The shipped document with the saved edits and audit trail in its edits block.

    The structure always comes from the shipped file, so a deploy that changes the help
    content shows up at once; the edits block comes from the edited copy.
    """
    shipped = SHIPPED_DOC.read_text(encoding="utf-8")
    if not EDITED_DOC.exists():
        return shipped
    return _with_edits(shipped, _parse_edits(EDITED_DOC.read_text(encoding="utf-8")))


def _parse_edits(html: str) -> dict:
    match = _EDITS_BLOCK.search(html)
    if not match:
        raise HTTPException(status_code=500, detail="Help document has no edits block")
    try:
        data = json.loads(match.group(2) or "{}")
    except json.JSONDecodeError:
        logger.error("Help document edits block is not valid JSON; starting a new one")
        data = {}
    edits = data.get("edits") if isinstance(data.get("edits"), dict) else {}
    audit = data.get("audit") if isinstance(data.get("audit"), list) else []
    feedback = data.get("feedback") if isinstance(data.get("feedback"), list) else []
    return {"edits": edits, "audit": audit, "feedback": feedback}


def _with_edits(html: str, data: dict) -> str:
    # Escape "<" so no text can close the script block early
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return _EDITS_BLOCK.sub(lambda m: m.group(1) + payload + m.group(3), html, count=1)


def _with_support_contact(html: str) -> str:
    email = os.getenv("HELP_SUPPORT_EMAIL", "").strip()
    if email and _EMAIL.match(email):
        return html.replace("{{SUPPORT_EMAIL}}", escape(email, quote=True))
    # No contact configured: drop the links, the surrounding text still reads correctly
    return re.sub(r'<a [^>]*class="support-link"[^>]*>.*?</a>', "", html, flags=re.DOTALL).replace(
        "{{SUPPORT_EMAIL}}", ""
    )


def _write_document(html: str) -> None:
    """Write atomically, so a reader never sees half a document."""
    EDITED_DOC.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(EDITED_DOC.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        os.replace(tmp, EDITED_DOC)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _check_section(html: str, section_id: str) -> None:
    if not _SECTION_ID.match(section_id) or f'data-edit-id="{section_id}"' not in html:
        raise HTTPException(status_code=400, detail="Unknown help section")


def _is_admin(user: AuthenticatedUser, db: Session) -> bool:
    db_user = db.query(User).filter(User.email == user.email).first()
    return bool(db_user and db_user.role and db_user.role.name.upper() == "ADMIN")


def _change(section_id: str, new_text, user: AuthenticatedUser) -> dict:
    with _lock:
        html = _read_document()
        _check_section(html, section_id)
        data = _parse_edits(html)
        before = data["edits"].get(section_id)  # None means the shipped text
        if new_text is None:
            data["edits"].pop(section_id, None)
        else:
            data["edits"][section_id] = new_text
        data["audit"].append(
            {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "by": user.email,
                "section": section_id,
                "action": "reset" if new_text is None else "edit",
                "before": before,
                "after": new_text,
            }
        )
        data["audit"] = data["audit"][-MAX_AUDIT:]
        _write_document(_with_edits(html, data))
    logger.info("Help section %s %s by %s", section_id, "reset" if new_text is None else "edited", user.email)
    return data


@router.get("/document", response_class=HTMLResponse)
async def get_document(user: AuthenticatedUser = Depends(require_auth), db: Session = Depends(get_db)):
    html = _read_document()
    if not _is_admin(user, db):
        # Only admins see who changed what, and the feedback
        data = _parse_edits(html)
        last_edit = data["audit"][-1]["at"] if data["audit"] else None
        html = _with_edits(html, {"edits": data["edits"], "audit": [], "feedback": [], "last_edit": last_edit})
    return HTMLResponse(_with_support_contact(html), headers={"Cache-Control": "no-store"})


@router.post("/edit")
async def edit_section(body: EditRequest, user: AuthenticatedUser = Depends(require_admin)):
    text = body.text.replace("\r\n", "\n").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty; use reset to restore the original")
    if len(text) > MAX_TEXT:
        raise HTTPException(status_code=400, detail=f"Text is longer than {MAX_TEXT} characters")
    return _change(body.section_id, text, user)


@router.post("/reset")
async def reset_section(body: ResetRequest, user: AuthenticatedUser = Depends(require_admin)):
    return _change(body.section_id, None, user)


@router.post("/feedback")
async def give_feedback(body: FeedbackRequest, user: AuthenticatedUser = Depends(require_auth)):
    comment = body.comment.replace("\r\n", "\n").strip()[:MAX_COMMENT]
    with _lock:
        html = _read_document()
        data = _parse_edits(html)
        data["feedback"].append(
            {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "by": user.email,
                "helpful": body.helpful,
                "comment": comment,
            }
        )
        data["feedback"] = data["feedback"][-MAX_FEEDBACK:]
        _write_document(_with_edits(html, data))
    logger.info("Help feedback from %s: %s", user.email, "helpful" if body.helpful else "not helpful")
    return {"status": "ok"}
