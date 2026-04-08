import sys
import os
import logging

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import engine, Base
# Import models to ensure they are registered with Base.metadata
from src.models import Role, User, Patient, Visit, Vital, Symptom, LifestyleFactor
from src.ui_translations import UITranslation

logging.basicConfig(level=logging.INFO)

def init_db():
    print("Initializing Aushadha Database Tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Successfully created all tables.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
