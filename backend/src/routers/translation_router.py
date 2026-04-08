"""
Translation Router — /translate
Provides UI string lookup with LLM auto-generation on cache miss.
"""
import logging
import asyncio
import json
import re
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api_response import create_api_response
from src.database import get_db
from src.llm import get_llm, llm_semaphore
from src.ui_translations import (
    SUPPORTED_LANG_CODES, LANG_NAMES, UITranslation,
    get_ui_translation, get_ui_translations_batch,
    upsert_ui_translation, bulk_upsert_ui_translations, get_coverage_stats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["translation"])

# Known UI strings are now managed dynamically in the PostgreSQL database.



# ─── Schemas ──────────────────────────────────────────────────────────────────
class TranslateSingleRequest(BaseModel):
    text: str
    lang: str
    model: Optional[str] = None  # LLM model override; uses default if absent


class TranslateBatchRequest(BaseModel):
    texts: list[str]
    lang: str
    model: Optional[str] = None


def _clean_llm_response(content: str) -> str:
    """Strip <think> blocks and markdown JSON formatting from LLM output."""
    # Strip <think>...</think> blocks
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    if "</think>" in content:
         content = content.split("</think>")[-1].strip()
    content = content.replace("<think>", "").strip()

    # Strip markdown code blocks
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    
    if content.endswith("```"):
        content = content[:-3]
    
    return content.strip()


def _parse_batch_translation_response(content: str) -> dict[str, str]:
    """Parse several JSON response shapes returned by translation models."""
    cleaned = _clean_llm_response(content)
    if not cleaned:
        return {}

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        if "translations" in parsed and isinstance(parsed["translations"], dict):
            return {str(k): str(v) for k, v in parsed["translations"].items()}
        if "items" in parsed and isinstance(parsed["items"], list):
            normalized: dict[str, str] = {}
            for item in parsed["items"]:
                if isinstance(item, dict):
                    original = item.get("original_string") or item.get("source") or item.get("english")
                    translated = item.get("translated_string") or item.get("translation") or item.get("target")
                    if original and translated:
                        normalized[str(original)] = str(translated)
            if normalized:
                return normalized
        if all(isinstance(v, str) for v in parsed.values()):
            return {str(k): str(v) for k, v in parsed.items()}

    if isinstance(parsed, list):
        normalized: dict[str, str] = {}
        for item in parsed:
            if isinstance(item, dict):
                original = item.get("original_string") or item.get("source") or item.get("english")
                translated = item.get("translated_string") or item.get("translation") or item.get("target")
                if original and translated:
                    normalized[str(original)] = str(translated)
        if normalized:
            return normalized

    # Sarvam can return comma-separated JSON objects without surrounding brackets.
    wrapped = f"[{cleaned}]" if not cleaned.lstrip().startswith("[") else cleaned
    parsed_list = json.loads(wrapped)
    normalized: dict[str, str] = {}
    for item in parsed_list:
        if isinstance(item, dict):
            original = item.get("original_string") or item.get("source") or item.get("english")
            translated = item.get("translated_string") or item.get("translation") or item.get("target")
            if original and translated:
                normalized[str(original)] = str(translated)
    return normalized

def _get_translation_params(lang_code: str, model: Optional[str]):
    """Pick the translation model and user-facing language name."""
    indian_langs = {"hi", "ta", "te", "kn", "ml", "mr", "gu", "bn", "or", "pa", "as", "ur"}
    llm_model = model or ("SARVAM" if lang_code in indian_langs else "OPENAI_GPT_5_2")
    llm, _, _ = get_llm(llm_model)
    lang_name = LANG_NAMES.get(lang_code, lang_code)
    return llm, lang_name


async def _llm_translate(text: str, lang_code: str, model: Optional[str] = None):
    """Internal: invoke LLM for a single string translation."""
    from langchain_core.messages import HumanMessage, SystemMessage
    try:
        llm, lang_name = _get_translation_params(lang_code, model)
        messages = [
            SystemMessage(content=(
                f"You are a professional medical translator into {lang_name}. "
                "Translate the provided text accurately. Keep medical terminology precise. "
                "Output ONLY the translated text, no explanation."
            )),
            HumanMessage(content=f"Translate to {lang_name}:\n{text}"),
        ]
        async with llm_semaphore:
            response = await llm.ainvoke(messages)
            return _clean_llm_response(response.content)
    except Exception as e:
        logger.error(f"LLM translation critical failure for '{text}' → {lang_code}: {str(e)}", exc_info=True)
        return None


async def _llm_translate_batch(texts: list[str], lang_code: str, model: Optional[str] = None):
    """Internal: invoke LLM for batch translation of multiple strings."""
    from langchain_core.messages import HumanMessage, SystemMessage
    try:
        if not texts:
            return {}
        llm, lang_name = _get_translation_params(lang_code, model)
        messages = [
            SystemMessage(content=(
                f"You are a professional medical translator into {lang_name}. "
                "Translate the provided JSON list of strings. Maintain precision. "
                "Return a JSON object: { \"original_string\": \"translated_string\" }. "
                "NO extra text."
            )),
            HumanMessage(content=json.dumps(texts)),
        ]
        async with llm_semaphore:
            response = await llm.ainvoke(messages)
            return _parse_batch_translation_response(response.content)
    except Exception as e:
        logger.error(f"LLM batch translation critical failure for {len(texts)} texts → {lang_code}: {str(e)}", exc_info=True)
        return {}


# ─── DB Access Helpers ────────────────────────────────────────────────────────
@router.get("/ui/strings")
def get_known_ui_strings(db: Session = Depends(get_db)):
    """Return all distinct English UI keys present in the translation table."""
    db_strings = [r[0] for r in db.query(UITranslation.english_key).distinct().all()]
    return {"strings": sorted(db_strings)}


@router.post("/ui/register")
def register_ui_strings(texts: list[str], db: Session = Depends(get_db)):
    """
    Registers new English UI strings into the database if they don't exist.
    This enables dynamic/incremental discovery from the frontend.
    """
    entries = [{"english_key": t, "lang_code": "en", "value": t} for t in texts]
    count = bulk_upsert_ui_translations(db, entries)
    return {"registered": count, "total": len(texts)}


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/ui")
async def translate_ui_string(req: TranslateSingleRequest, db: Session = Depends(get_db)):
    """
    Translate a single UI string. Checks cache first.
    If not cached, uses LLM (Sarvam for Indian langs, GPT for others) and saves.
    """
    source_text = req.text.strip()
    if not source_text or req.lang == "en":
        return create_api_response("Success", data={"translated": source_text})

    # 1. Check cache
    cached = get_ui_translation(db, source_text, req.lang)
    if cached:
        return create_api_response("Success", data={"translated": cached, "cached": True})

    # 2. Translate via LLM
    translated = await _llm_translate(source_text, req.lang)
    if not translated:
        return create_api_response("Failed", message="Translation failed")

    # 3. Save to cache
    from src.ui_translations import upsert_ui_translation
    upsert_ui_translation(db, source_text, req.lang, translated)
    return create_api_response("Success", data={"translated": translated, "cached": False})


@router.post("/ui/batch")
async def translate_ui_batch(req: TranslateBatchRequest, db: Session = Depends(get_db)):
    """
    Efficient batch translation for UI strings. 
    Returns a mapping of { 'english': 'target' }.
    """
    if not req.texts or req.lang == "en":
        return create_api_response("Success", data={t: t for t in req.texts})

    # 1. Batch retrieval from cache
    translated_map = get_ui_translations_batch(db, req.texts, req.lang)
    
    # 2. Identify misses
    misses = [t for t in req.texts if not translated_map.get(t)]
    
    if misses:
        logger.info(f"Translating {len(misses)} UI strings via LLM to {req.lang}")
        new_translations: dict[str, str] = {}
        batch_size = 12
        for index in range(0, len(misses), batch_size):
            chunk = misses[index:index + batch_size]
            chunk_translations = await _llm_translate_batch(chunk, req.lang)
            if not chunk_translations:
                logger.warning(f"Batch chunk failed for {req.lang}; falling back to single-string translation for {len(chunk)} items")
                for text in chunk:
                    translated = await _llm_translate(text, req.lang)
                    if translated:
                        chunk_translations[text] = translated
            new_translations.update(chunk_translations)
        
        # 3. Save new ones to DB
        if new_translations:
            entries = [
                {"english_key": k, "lang_code": req.lang, "value": v}
                for k, v in new_translations.items()
            ]
            bulk_upsert_ui_translations(db, entries)
            translated_map.update(new_translations)

    return create_api_response("Success", data=translated_map)


@router.get("/ui/stats")
def translation_stats(db: Session = Depends(get_db)):
    """Return translation coverage stats per language."""
    return get_coverage_stats(db)


@router.post("/ui/seed")
async def seed_translations(
    lang: Optional[str] = None,
    model: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Admin: pre-populate all known UI strings for a language (or all languages).
    Skips strings already translated.
    """
    target_langs = [lang] if lang else [c for c in SUPPORTED_LANG_CODES if c != "en"]
    total = 0

    # Get all distinct keys from DB to seed
    db_keys = [r[0] for r in db.query(UITranslation.english_key).distinct().all()]

    for lc in target_langs:
        if lc not in SUPPORTED_LANG_CODES:
            continue
        cached_map = get_ui_translations_batch(db, db_keys, lc)
        misses = [t for t, v in cached_map.items() if not v]
        if not misses:
            continue
        tasks = [_llm_translate(t, lc, model) for t in misses]
        results = await asyncio.gather(*tasks)
        entries = [{"english_key": t, "lang_code": lc, "value": v} for t, v in zip(misses, results) if v]
        if entries:
            count = bulk_upsert_ui_translations(db, entries)
            total += count
            logger.info(f"Seeded {len(entries)} strings for lang={lc}")

    return {"seeded": total, "languages": target_langs}
