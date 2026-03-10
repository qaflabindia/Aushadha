import sys
import os
import uuid

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.database import SessionLocal
from src.models import User, Role, Patient

def fix_all(admin_email, patient_emails):
    db = SessionLocal()
    try:
        # 1. Update Admin Role
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if not admin_role:
            admin_role = Role(name="Admin")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        
        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            print(f"User {admin_email} not found. Creating as Admin.")
            user = User(email=admin_email, role_id=admin_role.id)
            db.add(user)
        else:
            print(f"Updating {admin_email} to Admin role.")
            user.role_id = admin_role.id
        db.commit()
        db.refresh(user)

        # 2. Ensure Patient role exists
        patient_role = db.query(Role).filter(Role.name == "Patient").first()
        if not patient_role:
            patient_role = Role(name="Patient")
            db.add(patient_role)
            db.commit()
            db.refresh(patient_role)

        # 3. Process Patients
        for p_email in patient_emails:
            # Find or Create Patient User
            p_user = db.query(User).filter(User.email == p_email).first()
            if not p_user:
                print(f"Creating Patient User: {p_email}")
                p_user = User(email=p_email, role_id=patient_role.id)
                db.add(p_user)
                db.commit()
                db.refresh(p_user)
            
            # Ensure Patient Record exists
            patient = db.query(Patient).filter(Patient.user_id == p_user.id).first()
            if not patient:
                case_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
                print(f"Creating Patient Record for {p_email} with Case ID: {case_id}")
                patient = Patient(
                    case_id=case_id,
                    user_id=p_user.id,
                    age_group="Unknown",
                    sex="Unknown"
                )
                db.add(patient)
                db.commit()
                db.refresh(patient)
            
            # Assign to Admin User
            if patient not in user.assigned_patients:
                user.assigned_patients.append(patient)
                print(f"Assigned {p_email} (Case: {patient.case_id}) to {admin_email}")
            else:
                print(f"{p_email} already assigned to {admin_email}")
        
        db.commit()
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    admin_email_to_fix = "lakshminarasimhan.santhanam@gigkri.com"
    patients_to_assign = [
        "sln2737@gmail.com",
        "sridevi1977@gmail.com",
        "root.parent@gmail.com",
        "qaflabindia@gmail.com"
    ]
    fix_all(admin_email_to_fix, patients_to_assign)
