"""
Translation Cache — PostgreSQL-backed cache for translations.
Medical terminology and all translated terms are stored locally.
Only NEW/unseen terms are sent to the Sarvam AI Cloud API.
"""
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal

logger = logging.getLogger(__name__)


class TranslationCache(Base):
    __tablename__ = "translation_cache"

    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(String, index=True, nullable=False)
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
        db.commit()
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
