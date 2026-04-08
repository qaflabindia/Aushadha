import sys
import os
import uuid

# Add src to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.database import SessionLocal
from src.models import User, Role, Patient

def assign_patient_role(email: str):
    db = SessionLocal()
    try:
        # Get or create Patient role
        role = db.query(Role).filter(Role.name == "Patient").first()
        if not role:
            role = Role(name="Patient")
            db.add(role)
            db.commit()
            db.refresh(role)
            
        print(f"Role ID for Patient is {role.id}")
        
        # Get or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Creating new user {email}")
            user = User(email=email, role_id=role.id)
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print(f"Updating existing user {email}")
            user.role_id = role.id
            db.commit()
            
        # Ensure Patient record exists
        patient_record = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient_record:
            case_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
            print(f"Creating patient record with case ID {case_id} for user {email}")
            new_patient = Patient(
                case_id=case_id,
                user_id=user.id,
                age_group="Unknown",
                sex="Unknown"
            )
            db.add(new_patient)
            db.commit()
        else:
            print(f"Patient record already exists for {email} with case ID {patient_record.case_id}")
            
    finally:
        db.close()

if __name__ == "__main__":
    assign_patient_role("sln2737@gmail.com")
    assign_patient_role("root.parent@gmail.com")
    print("Done")
