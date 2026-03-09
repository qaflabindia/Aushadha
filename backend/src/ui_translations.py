"""
UI Translation Table — columnar PostgreSQL model.
One row per English phrase, 22 language columns.
On cache miss, the configured LLM auto-generates and persists the value.
"""
import logging
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Session
from .database import Base, engine

logger = logging.getLogger(__name__)

# ─── 22 supported languages ───────────────────────────────────────────────────
SUPPORTED_LANG_CODES = [
    "en", "hi", "ta", "te", "bn", "mr", "kn", "ml",
    "gu", "pa", "or", "as", "ur", "fr", "de", "es",
    "zh", "ja", "ko", "ar", "ru", "pt",
]

LANG_NAMES = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam",
    "gu": "Gujarati", "pa": "Punjabi", "or": "Odia", "as": "Assamese",
    "ur": "Urdu", "fr": "French", "de": "German", "es": "Spanish",
    "zh": "Chinese (Simplified)", "ja": "Japanese", "ko": "Korean",
    "ar": "Arabic", "ru": "Russian", "pt": "Portuguese",
}


class UITranslation(Base):
    __tablename__ = "ui_translations"

    id = Column(Integer, primary_key=True, index=True)
    english_key = Column(String(512), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 22 language columns
    en = Column(Text, nullable=True)
    hi = Column(Text, nullable=True)
    ta = Column(Text, nullable=True)
    te = Column(Text, nullable=True)
    bn = Column(Text, nullable=True)
    mr = Column(Text, nullable=True)
    kn = Column(Text, nullable=True)
    ml = Column(Text, nullable=True)
    gu = Column(Text, nullable=True)
    pa = Column(Text, nullable=True)
    or_ = Column("or", Text, nullable=True)   # 'or' is a Python keyword
    as_ = Column("as", Text, nullable=True)   # 'as' is a Python keyword
    ur = Column(Text, nullable=True)
    fr = Column(Text, nullable=True)
    de = Column(Text, nullable=True)
    es = Column(Text, nullable=True)
    zh = Column(Text, nullable=True)
    ja = Column(Text, nullable=True)
    ko = Column(Text, nullable=True)
    ar = Column(Text, nullable=True)
    ru = Column(Text, nullable=True)
    pt = Column(Text, nullable=True)


def ensure_table():
    UITranslation.__table__.create(bind=engine, checkfirst=True)
    logger.info("ui_translations table ensured.")


def _col_attr(lang_code: str) -> str:
    """Map lang code to SQLAlchemy attribute name (handles Python keywords)."""
    return {"or": "or_", "as": "as_"}.get(lang_code, lang_code)


def get_ui_translation(db: Session, english_key: str, lang_code: str) -> str | None:
    """
    Look up a single translation.
    Returns the translated string, or None if the row/column is missing.
    """
    if lang_code not in SUPPORTED_LANG_CODES:
        return None
    row = db.query(UITranslation).filter(
        UITranslation.english_key == english_key.strip()
    ).first()
    if not row:
        return None
    return getattr(row, _col_attr(lang_code), None)


def get_ui_translations_batch(
    db: Session, english_keys: list[str], lang_code: str
) -> dict[str, str | None]:
    """
    Batch lookup: returns {english_key: translated_value | None} for all keys.
    """
    if lang_code not in SUPPORTED_LANG_CODES:
        return {k: None for k in english_keys}
    rows = db.query(UITranslation).filter(
        UITranslation.english_key.in_([k.strip() for k in english_keys])
    ).all()
    attr = _col_attr(lang_code)
    result = {k: None for k in english_keys}
    for row in rows:
        result[row.english_key] = getattr(row, attr, None)
    return result


def upsert_ui_translation(
    db: Session, english_key: str, lang_code: str, value: str
) -> UITranslation:
    """Insert or update a single language column for a given English key."""
    if lang_code not in SUPPORTED_LANG_CODES:
        raise ValueError(f"Unsupported lang: {lang_code}")
    key = english_key.strip()
    row = db.query(UITranslation).filter(UITranslation.english_key == key).first()
    if not row:
        row = UITranslation(english_key=key, en=key)   # English = key itself
        db.add(row)
    setattr(row, _col_attr(lang_code), value)
    db.commit()
    db.refresh(row)
    return row


def bulk_upsert_ui_translations(
    db: Session, entries: list[dict]
) -> int:
    """
    Bulk insert/update. Each dict: {english_key, lang_code, value}.
    Returns count of rows processed.
    """
    count = 0
    for entry in entries:
        try:
            upsert_ui_translation(db, entry["english_key"], entry["lang_code"], entry["value"])
            count += 1
        except Exception as e:
            logger.warning(f"Bulk upsert skip: {e}")
    return count


def get_coverage_stats(db: Session) -> dict:
    """Return translation coverage counts per language."""
    total = db.query(func.count(UITranslation.id)).scalar() or 0
    stats = {"total_keys": total, "by_language": {}}
    for code in SUPPORTED_LANG_CODES:
        attr = _col_attr(code)
        col = getattr(UITranslation, attr)
        count = db.query(func.count(UITranslation.id)).filter(col.isnot(None)).scalar() or 0
        stats["by_language"][code] = {"name": LANG_NAMES[code], "translated": count, "missing": total - count}
    return stats
