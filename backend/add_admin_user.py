import sys
import os

# Add the /code directory to sys.path to import src modules
sys.path.append('/code')

from src.database import SessionLocal
from src.models import User, Role

def add_admin(email):
    db = SessionLocal()
    try:
        # 1. Ensure Admin role exists
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if not admin_role:
            admin_role = Role(name="Admin")
            db.add(admin_role)
            db.flush()
            print("Created 'Admin' role.")
        else:
            print("'Admin' role exists.")

        # 2. Add or update user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                role_id=admin_role.id
            )
            db.add(user)
            print(f"Added user {email} as Admin.")
        else:
            user.role_id = admin_role.id
            print(f"Updated user {email} to Admin role.")
        
        db.commit()
        print("Done.")
    except Exception as e:
        db.rollback()
        print(f"Error adding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    target_email = "lakshminarasimhan.santhanam@gigkri.com"
    add_admin(target_email)
