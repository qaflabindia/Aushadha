# =============================================================================
# Aushadha — Admin Elevation Script
# =============================================================================
# Usage: python backend/scripts/elevate_admin.py <email>
# =============================================================================

import sys
import os

# Add backend to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import SessionLocal
from src.models import User, Role

def elevate_user(email):
    db = SessionLocal()
    try:
        # 1. Ensure Admin role exists
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if not admin_role:
            print("Creating Admin role...")
            admin_role = Role(name="Admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        
        # 2. Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found. Creating new user...")
            user = User(email=email, role_id=admin_role.id)
            db.add(user)
        else:
            print(f"User {email} found. Elevating to Admin...")
            user.role_id = admin_role.id
        
        db.commit()
        print(f"SUCCESS: {email} is now an Admin.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    target_email = "lakshminarasimhan.santhanam@gigkri.com"
    if len(sys.argv) > 1:
        target_email = sys.argv[1]
    
    elevate_user(target_email)
