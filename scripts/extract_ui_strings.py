#!/usr/bin/env python3
"""Collect the frontend's translatable UI strings into backend/ui_strings.json.

Finds every t('...') / t("...") call with a literal argument in frontend/src and
resolves camelCase keys (e.g. 'fileManagement') to the English label the UI shows,
using frontend/src/utils/labels.ts. The backend's seed_ui_translations.py reads the
JSON to register and translate these strings.

Run from the repository root after changing UI text:
    python3 scripts/extract_ui_strings.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"
LABELS = SRC / "utils" / "labels.ts"
OUT = ROOT / "backend" / "ui_strings.json"

T_CALL = re.compile(r"""\bt\(\s*(['"])((?:\\.|(?!\1).)+)\1\s*[,)]""")
LABEL_ENTRY = re.compile(r"""^\s*([A-Za-z0-9_]+):\s*(['"])((?:\\.|(?!\2).)*)\2,?\s*$""")
CAMEL_KEY = re.compile(r"^[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*$")


def unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def load_labels() -> dict:
    labels = {}
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        m = LABEL_ENTRY.match(line)
        if m:
            labels[m.group(1)] = unescape(m.group(3))
    return labels


def resolve(key: str, labels: dict) -> str:
    """Mirror resolveLabel() in labels.ts."""
    if key in labels:
        return labels[key]
    if CAMEL_KEY.match(key):
        words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key).lower()
        return words[0].upper() + words[1:]
    return key


def main() -> None:
    labels = load_labels()
    strings = set()
    for path in sorted(SRC.rglob("*.ts*")):
        if "_old" in path.name:
            continue
        for m in T_CALL.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            text = resolve(unescape(m.group(2)), labels).strip()
            if text:
                strings.add(text)
    OUT.write_text(json.dumps(sorted(strings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(strings)} UI strings to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
