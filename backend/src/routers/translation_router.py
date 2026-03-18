"""
Translation Router — /translate
Provides UI string lookup with LLM auto-generation on cache miss.
"""
import logging
import os
import asyncio
import json
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.ui_translations import (
    SUPPORTED_LANG_CODES, LANG_NAMES, UITranslation,
    ensure_table, get_ui_translation, get_ui_translations_batch,
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


# ─── LLM auto-generation ──────────────────────────────────────────────────────
# ─── LLM auto-generation helpers ──────────────────────────────────────────────
def _get_translation_params(lang_code: str, model: Optional[str]):
    """Unified logic for LLM selection and medical context setup."""
    from src.llm import get_llm
    
    INDIAN_LANGS = ["hi", "ta", "te", "kn", "ml", "mr", "gu", "bn", "or", "pa"]
    if model:
        llm_model = model
    elif lang_code in INDIAN_LANGS:
        llm_model = "SARVAM"
    else:
        llm_model = "GEMINI-PRO"

    llm, _, _ = get_llm(llm_model)
    lang_name = LANG_NAMES.get(lang_code, lang_code)
    
    context_hint = (
        "This is for AyushPragya, a specialized clinical AI platform for Indian healthcare (AYUSH/Medical). "
        "Ensure the translation is professional, medically accurate where applicable, and colloquially appropriate for healthcare providers."
    )
    return llm, lang_name, context_hint


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


async def _llm_translate(text: str, lang_code: str, model: Optional[str] = None) -> Optional[str]:
    """Use the configured LLM to translate a UI string from English to lang_code."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        llm, lang_name, context_hint = _get_translation_params(lang_code, model)

        messages = [
            SystemMessage(content=(
                f"You are a professional medical UI translator for an Indian healthcare platform. "
                f"{context_hint} "
                f"Translate the given English UI label to {lang_name}. "
                f"Return ONLY the translated text — no quotes, no explanations, no notes."
            )),
            HumanMessage(content=f"Translate to {lang_name}:\n{text}"),
        ]
        response = await llm.ainvoke(messages)
        return _clean_llm_response(response.content)
    except Exception as e:
        logger.error(f"LLM translation critical failure for '{text}' → {lang_code}: {str(e)}", exc_info=True)
        return None


async def _llm_translate_batch(texts: list[str], lang_code: str, model: Optional[str] = None) -> dict[str, str]:
    """Use the configured LLM to translate a batch of UI strings from English to lang_code."""
    if not texts: return {}
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        llm, lang_name, context_hint = _get_translation_params(lang_code, model)

        messages = [
            SystemMessage(content=(
                f"You are a professional medical UI translator. {context_hint} "
                f"Translate the following list of English UI strings to {lang_name}. "
                f"Return ONLY a valid JSON object where the keys are the EXACT original English strings and the values are their {lang_name} translations. Do not include markdown formatting or quotes around the JSON text."
            )),
            HumanMessage(content=json.dumps(texts)),
        ]
        response = await llm.ainvoke(messages)
        return json.loads(_clean_llm_response(response.content))
    except Exception as e:
        logger.error(f"LLM batch translation critical failure for {len(texts)} texts → {lang_code}: {str(e)}", exc_info=True)
        return {}


@router.get("/ui/strings")
def get_known_ui_strings(db: Session = Depends(get_db)):
    """Returns the master list of UI strings used for translation."""
    db_strings = [r[0] for r in db.query(UITranslation.english_key).distinct().all()]
    return {"strings": sorted(db_strings)}


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/ui")
async def translate_ui_string(req: TranslateSingleRequest, db: Session = Depends(get_db)):
    """
    Translate a single UI string.
    Looks up the DB; auto-generates and stores via LLM on cache miss.
    """
    if req.lang not in SUPPORTED_LANG_CODES:
        raise HTTPException(400, f"Unsupported language: {req.lang}")

    # English → return as-is
    if req.lang == "en":
        return {"text": req.text, "translated": req.text, "lang": req.lang, "source": "passthrough"}

    # DB lookup
    cached = get_ui_translation(db, req.text, req.lang)
    if cached:
        return {"text": req.text, "translated": cached, "lang": req.lang, "source": "cache"}

    # LLM auto-generate
    translated = await _llm_translate(req.text, req.lang, req.model)
    if translated:
        upsert_ui_translation(db, req.text, req.lang, translated)
        return {"text": req.text, "translated": translated, "lang": req.lang, "source": "llm"}
    else:
        return {"text": req.text, "translated": req.text, "lang": req.lang, "source": "fallback"}


@router.post("/ui/batch")
async def translate_ui_batch(req: TranslateBatchRequest, db: Session = Depends(get_db)):
    """
    Batch translate UI strings.
    Returns map of english_text → translated string.
    Cache hits are instant; misses are auto-generated in parallel via LLM.
    """
    if req.lang not in SUPPORTED_LANG_CODES:
        raise HTTPException(400, f"Unsupported language: {req.lang}")

    if req.lang == "en":
        return {"lang": req.lang, "translations": {t: t for t in req.texts}}

    # Batch DB lookup
    cached_map = get_ui_translations_batch(db, req.texts, req.lang)

    # Identfy cache misses
    misses = [text for text, val in cached_map.items() if not val]

    if misses:
        logger.info(f"[TRANSLATE BATCH] {len(misses)} cache misses for lang={req.lang}, auto-generating with batch JSON...")
        
        chunk_size = 50
        for i in range(0, len(misses), chunk_size):
            chunk = misses[i:i + chunk_size]
            results = await _llm_translate_batch(chunk, req.lang, req.model)
            
            for text in chunk:
                translated = results.get(text)
                if translated:
                    cached_map[text] = translated
                    upsert_ui_translation(db, text, req.lang, translated)
                else:
                    cached_map[text] = text # fallback for the UI

    return {"lang": req.lang, "translations": cached_map}


@router.post("/dynamic/batch")
async def translate_dynamic_batch(req: TranslateBatchRequest, db: Session = Depends(get_db)):
    """
    Batch translate dynamic graph tokens (node labels, relationship types).
    Uses the same underlying cache and LLM logic as UI strings.
    """
    if req.lang not in SUPPORTED_LANG_CODES:
        raise HTTPException(400, f"Unsupported language: {req.lang}")

    if req.lang == "en":
        return {"lang": req.lang, "translations": {t: t for t in req.texts}}

    # Identify cache hits/misses
    cached_map = get_ui_translations_batch(db, req.texts, req.lang)
    misses = [text for text, val in cached_map.items() if not val]

    if misses:
        logger.info(f"[TRANSLATE DYNAMIC] {len(misses)} tokens missing for lang={req.lang}")
        tasks = [_llm_translate(t, req.lang, req.model) for t in misses]
        results = await asyncio.gather(*tasks)

        for text, translated in zip(misses, results):
            if translated:
                cached_map[text] = translated
                upsert_ui_translation(db, text, req.lang, translated)
            else:
                cached_map[text] = text

    return {"lang": req.lang, "translations": cached_map}


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
