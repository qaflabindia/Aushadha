"""
Translation Cache — PostgreSQL-backed cache for translations.
Medical terminology and all translated terms are stored locally.
Only NEW/unseen terms are sent to the Sarvam AI Cloud API.
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal

logger = logging.getLogger(__name__)


class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(String(2048), index=True, nullable=False)
    source_lang = Column(String(10), nullable=False, default="en")
    target_lang = Column(String(10), nullable=False)
    translated_text = Column(String, nullable=False)
    is_medical_term = Column(Boolean, default=False)
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source_text", "source_lang", "target_lang", name="uq_translation"),
    )


def ensure_table():
    """Create the translation_cache table if it doesn't exist."""
    TranslationCache.__table__.create(bind=engine, checkfirst=True)
    logger.info("translation_cache table ensured.")


def get_cached_batch(db: Session, source_texts: List[str], source_lang: str, target_lang: str) -> dict[str, Optional[str]]:
    """
    Look up multiple cached translations in a single query.
    Returns a dictionary mapping sanitized source_text to translated_text.
    """
    if not source_texts:
        return {}

    sanitized_map = {t.lower().strip(): t for t in source_texts}
    sanitized_keys = list(sanitized_map.keys())

    rows = (
        db.query(TranslationCache)
        .filter(
            func.lower(TranslationCache.source_text).in_(sanitized_keys),
            TranslationCache.source_lang == source_lang,
            TranslationCache.target_lang == target_lang,
        )
        .all()
    )

    result = {t: None for t in source_texts}
    for row in rows:
        original_key = sanitized_map.get(row.source_text.lower().strip())
        if original_key:
            result[original_key] = row.translated_text
            # Optional: increment hit count in background or batch if needed
    
    return result


def get_cached(db: Session, source_text: str, source_lang: str, target_lang: str):
    """
    Look up a cached translation. Increments hit_count on cache hit.
    Returns translated_text or None.
    """
    row = (
        db.query(TranslationCache)
        .filter(
            func.lower(TranslationCache.source_text) == source_text.lower().strip(),
            TranslationCache.source_lang == source_lang,
            TranslationCache.target_lang == target_lang,
        )
        .first()
    )
    if row:
        row.hit_count += 1
        # db.commit()  # Removed write-on-read to reduce DB overhead. 
        # Metric remains accurate enough without instant persistence.
        return row.translated_text
    return None


def save_to_cache(
    db: Session,
    source_text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
    is_medical_term: bool = False,
):
    """Save a new translation to the cache. Skips if already exists."""
    existing = (
        db.query(TranslationCache)
        .filter(
            func.lower(TranslationCache.source_text) == source_text.lower().strip(),
            TranslationCache.source_lang == source_lang,
            TranslationCache.target_lang == target_lang,
        )
        .first()
    )
    if existing:
        return existing

    entry = TranslationCache(
        source_text=source_text.strip(),
        source_lang=source_lang,
        target_lang=target_lang,
        translated_text=translated_text,
        is_medical_term=is_medical_term,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(f"Cached: '{source_text}' → '{translated_text}' [{source_lang}→{target_lang}]")
    return entry


def get_cache_stats(db: Session):
    """Return cache statistics."""
    total = db.query(func.count(TranslationCache.id)).scalar() or 0
    medical = (
        db.query(func.count(TranslationCache.id))
        .filter(TranslationCache.is_medical_term == True)
        .scalar()
        or 0
    )
    total_hits = db.query(func.sum(TranslationCache.hit_count)).scalar() or 0
    langs = (
        db.query(TranslationCache.target_lang, func.count(TranslationCache.id))
        .group_by(TranslationCache.target_lang)
        .all()
    )
    return {
        "total_cached": total,
        "medical_terms": medical,
        "total_cache_hits": total_hits,
        "by_language": {lang: count for lang, count in langs},
    }
