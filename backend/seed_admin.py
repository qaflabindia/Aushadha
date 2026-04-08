import sys
import os
import bcrypt
from sqlalchemy.orm import Session

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal
from src.models import User, Role

def hash_password(password: str) -> str:
    # bcrypt requires bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def seed_admin():
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
            print("'Admin' role already exists.")

        # 2. Seed admin users
        admin_emails = ["admin", "lakshminarasimhan.santhanam@gigkri.com"]
        for email in admin_emails:
            db_user = db.query(User).filter(User.email == email).first()
            if not db_user:
                hashed_pw = hash_password("password")
                db_user = User(
                    email=email,
                    hashed_password=hashed_pw,
                    role_id=admin_role.id
                )
                db.add(db_user)
                print(f"Provisioned admin user: {email} / password")
            else:
                # Update role and password
                db_user.role_id = admin_role.id
                db_user.hashed_password = hash_password("password")
                print(f"Admin user {email} updated/role ensured.")
        
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error seeding admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
