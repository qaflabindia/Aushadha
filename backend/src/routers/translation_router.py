"""
Translation Router — /translate
Provides UI string lookup with LLM auto-generation on cache miss.
"""
import logging
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.ui_translations import (
    SUPPORTED_LANG_CODES, LANG_NAMES,
    ensure_table, get_ui_translation, get_ui_translations_batch,
    upsert_ui_translation, bulk_upsert_ui_translations, get_coverage_stats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["translation"])

# ─── Known UI strings — seeded into DB at startup ────────────────────────────
KNOWN_UI_STRINGS = [
    "File Management", "Clinical Intelligence", "DB Connection",
    "No Graph Schema configured", "Name", "Status", "Upload Status",
    "Size (KB)", "Source", "Type", "Model", "Nodes", "Completed",
    "Uploaded", "Local File", "Generate Graph", "Delete Files",
    "Preview Graph", "Graph Settings", "LLM Model for Processing & Chat",
    "Intelligence Search", "Medical Intelligence", "Select Language",
    "Data Insights", "Knowledge Graph", "Secret Vault", "Generated Graph",
    "We are visualizing 50 chunks at a time", "Document & Chunk",
    "Entities", "Result Overview", "Total Nodes", "Relationships",
    "Search On Node Properties", "Inquire Vault Intelligence",
    "Authorized Terminal", "Concierge Intelligence", "Details", "Show",
    "Page", "Large files may be partially processed up to 10K characters due to resource limit.",
    "Welcome to Concierge Intelligence. You can ask questions related to documents which have been completely processed.",
    "AyushPragya Medical Neural Network", "Select one or more files to delete",
    "Preview generated graph.", "Visualize the graph in Bloom",
    "File/Files to be deleted", "Documentation", "GitHub Issues",
    "Light / Dark mode", "Entity Graph Extraction Settings", "Start a chat",
    "Upload files", "Delete", "Maximise", "Copy to Clipboard", "Copied",
    "Stop Speaking", "Text to Speech", "Define schema from text",
    "Fetch schema from database", "Clear Chat History", "Continue",
    "Clear configured Graph Schema", "Apply Graph Schema", "Chat",
    "Download Conversation", "Visualize Graph Schema",
    "Analyze instructions for schema", "Predefined Schema",
    "Data Importer JSON", "Explore Graph", "Preview Graph",
    "Documents, Images, Unstructured text", "Youtube", "GCS", "Amazon S3",
    "No Labels Found in the Database",
    "Drop your neo4j credentials file here",
    "Analyze text to extract graph schema", "Connect", "Disconnect",
    "Submit", "Connect to DB", "Cancel", "Apply",
    "Provide Additional Instructions for Entity Extractions",
    "Analyze Instructions",
    "Provide specific instructions for entity extraction, such as focusing on the key topics.",
    "JSON Documents",
    "Files are still processing, please select individual checkbox for deletion",
    "Cancel the processing job",
    "Entity Extraction Settings", "Disconnected Nodes", "Duplication Nodes", "Post Processing Jobs",
    # Login page
    "Clinical Intelligence Platform", "Sign in with credentials",
    "Continue in read-only mode", "Email", "Password",
    "Signing in...", "Sign In",
    # SideNav
    "Patient Insights", "Global Research", "Administration", "AI Assistant",
    # Popups
    "Are you sure you want to delete the selected files?",
    "This action cannot be undone.", "Confirm", "Close",
    "Large file detected", "File exceeds recommended size",
    "Retry", "Processing failed. Would you like to retry?",
    "No labels found", "Connection settings", "Vector index mismatch",
]


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
async def _llm_translate(text: str, lang_code: str, model: Optional[str] = None) -> Optional[str]:
    """Use the configured LLM to translate a UI string from English to lang_code."""
    try:
        from src.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        llm_model = model or os.getenv("DEFAULT_TRANSLATION_MODEL", "SARVAM")
        llm, _, _ = get_llm(llm_model)
        lang_name = LANG_NAMES.get(lang_code, lang_code)

        messages = [
            SystemMessage(content=(
                f"You are a professional UI translator for a clinical intelligence platform used in Indian healthcare. "
                f"Translate the given English UI label to {lang_name}. "
                f"Return ONLY the translated text — no quotes, no explanations, no notes."
            )),
            HumanMessage(content=f"Translate to {lang_name}:\n{text}"),
        ]
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        
        # Strip <think>...</think> blocks if the model generates them
        import re
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()
        content = content.replace("<think>", "").strip()

        return content
    except Exception as e:
        logger.error(f"LLM translation failed for '{text}' → {lang_code}: {e}")
        return None   # signal failure so we don't save to DB


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

    # Identify cache misses
    import asyncio
    misses = [text for text, val in cached_map.items() if not val]

    if misses:
        logger.info(f"[TRANSLATE BATCH] {len(misses)} cache misses for lang={req.lang}, auto-generating...")
        tasks = [_llm_translate(t, req.lang, req.model) for t in misses]
        results = await asyncio.gather(*tasks)

        for text, translated in zip(misses, results):
            if translated:
                cached_map[text] = translated
                upsert_ui_translation(db, text, req.lang, translated)
            else:
                cached_map[text] = text # fallback for the UI

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
    import asyncio
    target_langs = [lang] if lang else [c for c in SUPPORTED_LANG_CODES if c != "en"]
    total = 0

    for lc in target_langs:
        if lc not in SUPPORTED_LANG_CODES:
            continue
        cached_map = get_ui_translations_batch(db, KNOWN_UI_STRINGS, lc)
        misses = [t for t, v in cached_map.items() if not v]
        if not misses:
            continue
        tasks = [_llm_translate(t, lc, model) for t in misses]
        results = await asyncio.gather(*tasks)
        entries = [{"english_key": t, "lang_code": lc, "value": v} for t, v in zip(misses, results) if v]
        if entries:
            total += bulk_upsert_ui_translations(db, entries)
            logger.info(f"Seeded {len(entries)} strings for lang={lc}")

    return {"seeded": total, "languages": target_langs}
