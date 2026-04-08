import os
import sys

from src.database import SessionLocal
from src.ui_translations import UITranslation, SUPPORTED_LANG_CODES, _col_attr
import logging

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
try:
    rows = db.query(UITranslation).all()
    count = 0
    for row in rows:
        modified = False
        for lang in SUPPORTED_LANG_CODES:
            if lang == "en": continue
            attr = _col_attr(lang)
            val = getattr(row, attr)
            if val and "<think>" in val:
                setattr(row, attr, None)
                modified = True
        if modified:
            count += 1
    db.commit()
    logging.info(f"Cleared {count} corrupted '<think>' rows.")
finally:
    db.close()
