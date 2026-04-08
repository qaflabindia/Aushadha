import sys
import os

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.database import SessionLocal
from src.models import User, Patient, user_patient_association

def check_assignments():
    db = SessionLocal()
    try:
        print("--- User Patient Assignments ---")
        assignments = db.execute(user_patient_association.select()).fetchall()
        if not assignments:
            print("No assignments found.")
        else:
            print(f"{'User ID':<10} | {'Patient ID':<10}")
            print("-" * 25)
            for row in assignments:
                # row is a tuple (user_id, patient_id)
                print(f"{row[0]:<10} | {row[1]:<10}")
        
        print("\n--- Users INFO ---")
        users = db.query(User).all()
        for u in users:
            role_name = u.role.name if u.role else "No Role"
            print(f"ID: {u.id}, Email: {u.email}, Role: {role_name}")

        print("\n--- Patients INFO ---")
        patients = db.query(Patient).all()
        for p in patients:
            print(f"ID: {p.id}, Case ID: {p.case_id}, User ID: {p.user_id}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_assignments()
