"""Register the frontend's UI strings, translate them, and verify coverage.

The list of strings comes from ui_strings.json (regenerate it with
scripts/extract_ui_strings.py after UI text changes). Translations use the same
models as the app: Sarvam for Indian languages, OpenAI for the rest.

Run inside the backend container:
    docker exec -w /code backend python seed_ui_translations.py               # all selector languages
    docker exec -w /code backend python seed_ui_translations.py --lang hi ta  # chosen languages
    docker exec -w /code backend python seed_ui_translations.py --verify-only # check, translate nothing

Exit code is 1 when any language is missing translations or has translations in
the wrong script, so the script can gate a deployment.
"""
import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=True)

from src.database import SessionLocal  # noqa: E402
from src.routers.translation_router import _llm_translate, _llm_translate_batch  # noqa: E402
from src.ui_translations import (  # noqa: E402
    LANG_NAMES,
    bulk_upsert_ui_translations,
    ensure_table,
    get_ui_translations_batch,
)

# Languages offered by the frontend language selector (frontend/src/context/LangTypes.ts)
SELECTOR_LANGS = ["hi", "ta", "te", "bn", "mr", "kn", "ml", "gu", "pa", "or"]

# Unicode block each language's translations should use
SCRIPTS = {
    "hi": r"ऀ-ॿ",
    "mr": r"ऀ-ॿ",
    "bn": r"ঀ-৿",
    "as": r"ঀ-৿",
    "pa": r"਀-੿",
    "gu": r"઀-૿",
    "or": r"଀-୿",
    "ta": r"஀-௿",
    "te": r"ఀ-౿",
    "kn": r"ಀ-೿",
    "ml": r"ഀ-ൿ",
}

BATCH_SIZE = 12
STRINGS_FILE = Path(__file__).with_name("ui_strings.json")


async def translate_missing(db, strings, lang):
    """Translate strings that have no stored translation yet; returns how many were added."""
    existing = get_ui_translations_batch(db, strings, lang)
    misses = [s for s in strings if not existing.get(s)]
    if not misses:
        return 0

    chunks = [misses[i : i + BATCH_SIZE] for i in range(0, len(misses), BATCH_SIZE)]
    results = await asyncio.gather(*(_llm_translate_batch(chunk, lang) for chunk in chunks))

    translated = {}
    for chunk, result in zip(chunks, results):
        result = {k: v for k, v in (result or {}).items() if k in chunk and v and str(v).strip()}
        # Fall back to one-by-one for anything the batch call dropped
        for text in chunk:
            if text not in result:
                single = await _llm_translate(text, lang)
                if single and single.strip():
                    result[text] = single
        translated.update(result)

    if translated:
        bulk_upsert_ui_translations(
            db, [{"english_key": k, "lang_code": lang, "value": v.strip()} for k, v in translated.items()]
        )
    return len(translated)


def verify(db, strings, lang):
    """Return (translated, missing, wrong_script, unchanged) for one language."""
    stored = get_ui_translations_batch(db, strings, lang)
    missing = [s for s in strings if not stored.get(s)]
    script = SCRIPTS.get(lang)
    wrong_script, unchanged = [], []
    for s in strings:
        value = stored.get(s)
        if not value:
            continue
        if value.strip() == s.strip():
            unchanged.append(s)  # often fine for brand names and acronyms; reported for review
        elif script and re.search(r"[A-Za-z]{2}", s) and not re.search(f"[{script}]", value):
            wrong_script.append(s)
    return len(strings) - len(missing), missing, wrong_script, unchanged


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lang", nargs="+", default=SELECTOR_LANGS, help="language codes (default: selector languages)")
    parser.add_argument("--verify-only", action="store_true", help="report coverage without translating")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    strings = json.loads(STRINGS_FILE.read_text(encoding="utf-8"))
    ensure_table()
    db = SessionLocal()
    try:
        # Register the English source strings so /translate/ui/strings returns them
        bulk_upsert_ui_translations(db, [{"english_key": s, "lang_code": "en", "value": s} for s in strings])
        print(f"Registered {len(strings)} English UI strings")

        if not args.verify_only:
            for lang in args.lang:
                added = asyncio.run(translate_missing(db, strings, lang))
                print(f"  {lang} ({LANG_NAMES.get(lang, lang)}): translated {added} new strings")

        print("\nCoverage")
        print(f"  {'lang':6s}{'translated':>12s}{'missing':>9s}{'wrong script':>14s}{'unchanged':>11s}")
        failed = False
        for lang in args.lang:
            done, missing, wrong, unchanged = verify(db, strings, lang)
            print(f"  {lang:6s}{done:>8d}/{len(strings):<3d}{len(missing):>9d}{len(wrong):>14d}{len(unchanged):>11d}")
            if missing or wrong:
                failed = True
                for label, items in (("missing", missing), ("wrong script", wrong)):
                    if items:
                        print(f"      {label}: " + "; ".join(items[:8]) + (" ..." if len(items) > 8 else ""))
        if failed:
            print("\nSome languages are incomplete. Re-run to retry missing strings.")
        else:
            print("\nAll languages fully translated.")
        return 1 if failed else 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
