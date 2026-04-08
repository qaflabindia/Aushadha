
import os
import sys
import re

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.getcwd()))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.database import SessionLocal
from src.translation_cache import TranslationCache

def is_rubbish(text, target_lang):
    """Detect if the translated text contains conversational 'rubbish'."""
    # Common conversational indicators in English
    rubbish_patterns = [
        r"intended translation",
        r"maybe",
        r"wait",
        r"the user wrote",
        r"medical term",
        r"here is the translation",
        r"it means",
        r"in tamil",
        r"in hindi"
    ]
    
    # If the target language is an Indian language but the text contains significant English conversational phrases
    if target_lang in ["hi", "ta", "te", "bn", "mr", "kn", "ml", "gu", "pa", "or"]:
        text_lower = text.lower()
        for pattern in rubbish_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Also check for high English word count in non-English target
        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        if len(english_words) > 3: # If more than 3 English words are found in a Tamil/Hindi translation
            return True
            
    return False

def clean_database():
    db = SessionLocal()
    try:
        rows = db.query(TranslationCache).all()
        rubbish_ids = []
        for row in rows:
            if is_rubbish(row.translated_text, row.target_lang):
                print(f"ID {row.id}: RUBBISH FOUND -> '{row.translated_text[:50]}...' (Target: {row.target_lang})")
                rubbish_ids.append(row.id)
        
        if rubbish_ids:
            print(f"Total rubbish rows found: {len(rubbish_ids)}")
            # For now, just print. We can delete them later.
            # db.query(TranslationCache).filter(TranslationCache.id.in_(rubbish_ids)).delete(synchronize_session=False)
            # db.commit()
            # print("Deleted rubbish rows.")
        else:
            print("No rubbish found.")
    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
