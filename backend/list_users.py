import sys
import os

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.database import SessionLocal
from src.models import User, Role

def list_users_and_roles():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"{'ID':<5} | {'Email':<30} | {'Role':<15}")
        print("-" * 55)
        for user in users:
            role_name = user.role.name if user.role else "No Role"
            print(f"{user.id:<5} | {user.email:<30} | {role_name:<15}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_users_and_roles()
