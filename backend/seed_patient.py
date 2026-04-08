import sys
import os
from sqlalchemy.orm import Session

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal
from src.models import User, Role, Patient

def seed_patient():
    db = SessionLocal()
    try:
        # 1. Ensure roles exist
        roles = ['Admin', 'Doctor', 'Staff', 'Patient']
        role_objs = {}
        for r_name in roles:
            role = db.query(Role).filter(Role.name == r_name).first()
            if not role:
                role = Role(name=r_name)
                db.add(role)
                db.flush()
                print(f"Created '{r_name}' role.")
            role_objs[r_name] = role

        # 2. Ensure admin user exists
        admin_user = db.query(User).filter(User.email == "admin").first()
        if not admin_user:
            admin_user = User(
                email="admin",
                role_id=role_objs['Admin'].id
            )
            db.add(admin_user)
            db.flush()
            print("Created 'admin' user.")
            
        # 3. Ensure the user 'lakshminarasimhan.santhanam@gigkri.com' is Admin
        user_email = "lakshminarasimhan.santhanam@gigkri.com"
        user = db.query(User).filter(User.email == user_email).first()
        if user:
            user.role_id = role_objs['Admin'].id
            print(f"Set {user_email} to Admin.")
        else:
            user = User(
                email=user_email,
                role_id=role_objs['Admin'].id
            )
            db.add(user)
            db.flush()
            print(f"Created {user_email} as Admin.")

        # 4. Ensure patient 'PT-AP-SANTHO' exists
        case_id = "PT-AP-SANTHO"
        patient = db.query(Patient).filter(Patient.case_id == case_id).first()
        if not patient:
            patient = Patient(
                case_id=case_id,
                age_group="45-55",
                sex="Male",
                user_id=user.id
            )
            db.add(patient)
            print(f"Seeded patient '{case_id}' in registry.")
        else:
            print(f"Patient '{case_id}' already exists.")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_patient()
