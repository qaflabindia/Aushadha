import sys
import os
from sqlalchemy.orm import Session

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal
from src.models import User, Patient, Role

def seed_user_patient():
    db = SessionLocal()
    try:
        user_email = "lakshminarasimhan.santhanam@gigkri.com"
        patient_case_id = "PT-AP-SANTHO"
        
        # 1. Ensure Role exists
        patient_role = db.query(Role).filter(Role.name == "Patient").first()
        if not patient_role:
            patient_role = Role(name="Patient")
            db.add(patient_role)
            db.flush()
        
        # 2. Ensure User exists
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(email=user_email, role_id=patient_role.id)
            db.add(user)
            db.flush()
            print(f"Created user: {user_email}")
        
        # 3. Ensure Patient exists
        patient = db.query(Patient).filter(Patient.case_id == patient_case_id).first()
        if not patient:
            patient = Patient(
                case_id=patient_case_id,
                user_id=user.id,
                age_group="Adult",
                sex="Male"
            )
            db.add(patient)
            db.commit()
            print(f"Created patient record: {patient_case_id} for user {user_email}")
        else:
            print(f"Patient record {patient_case_id} already exists.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding user/patient: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_user_patient()
