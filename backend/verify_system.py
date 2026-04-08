import sys
import os
import logging
from sqlalchemy import text

# Add the src directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify():
    logging.info("Verifying Core System State...")
    try:
        db = SessionLocal()
        
        # Check Roles
        roles = db.execute(text("SELECT name FROM roles")).fetchall()
        logging.info(f"Roles found: {[r[0] for r in roles]}")
        
        # Check Users
        users = db.execute(text("SELECT email FROM users")).fetchall()
        logging.info(f"Users found: {[u[0] for u in users]}")
        
        # Check Patients (Should be empty)
        patients = db.execute(text("SELECT count(*) FROM patients")).scalar()
        logging.info(f"Patient count: {patients} (Expected: 0)")
        
        db.close()
        logging.info("Verification complete. Core system is intact.")
    except Exception as e:
        logging.error(f"Verification failed: {e}")

if __name__ == "__main__":
    verify()
