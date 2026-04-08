import sys
import os
import bcrypt
from sqlalchemy.orm import Session

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal
from src.models import User

def test_login(username, password):
    db = SessionLocal()
    try:
        print(f"Testing login for: {username}")
        db_user = db.query(User).filter(User.email == username).first()
        if not db_user:
            print("User not found in DB.")
            return

        print(f"User found: {db_user.email}")
        print(f"Hashed password in DB: {db_user.hashed_password}")
        
        # Simulate verify_password
        try:
            plain_bytes = password.encode('utf-8')
            hashed_bytes = db_user.hashed_password.encode('utf-8')
            matches = bcrypt.checkpw(plain_bytes, hashed_bytes)
            print(f"Bcrypt check result: {matches}")
        except Exception as e:
            print(f"Bcrypt check error: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    test_login("admin", "password")
