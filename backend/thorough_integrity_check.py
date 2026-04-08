import sys
import os
from sqlalchemy import text
from sqlalchemy.orm import Session
from neo4j import GraphDatabase

# Add the current directory to sys.path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal
from src.models import User, Patient, Role
from src.shared.env_utils import get_value_from_env

def check_integrity():
    db = SessionLocal()
    print("--- Postgres Integrity Check ---")
    try:
        # 1. Total Counts
        user_count = db.query(User).count()
        patient_count = db.query(Patient).count()
        role_count = db.query(Role).count()
        print(f"Users: {user_count}")
        print(f"Patients: {patient_count}")
        print(f"Roles: {role_count}")

        # 2. Check for Users with Role 'Patient' but no Patient record
        patient_role = db.query(Role).filter(Role.name == "Patient").first()
        if patient_role:
            orphaned_users = db.query(User).filter(
                User.role_id == patient_role.id,
                ~User.id.in_(db.query(Patient.user_id).filter(Patient.user_id.isnot(None)))
            ).all()
            if orphaned_users:
                print(f"CRITICAL: Found {len(orphaned_users)} users with 'Patient' role but no linked Patient record.")
                for u in orphaned_users:
                    print(f" - Orphaned User: {u.email} (ID: {u.id})")
            else:
                print("OK: All users with 'Patient' role have linked Patient records (or are not yet assigned).")

        # 3. Check for Patients without a User
        orphaned_patients = db.query(Patient).filter(Patient.user_id.is_(None)).all()
        if orphaned_patients:
            print(f"WARNING: Found {len(orphaned_patients)} patients with no linked User (user_id is NULL).")
            for p in orphaned_patients:
                print(f" - Orphaned Patient: {p.case_id} (ID: {p.id})")

        # 4. Check for dangling assignments
        res = db.execute(text("SELECT user_id, patient_id FROM user_patient_assignment"))
        assignments = res.fetchall()
        print(f"Total Assignments: {len(assignments)}")

    except Exception as e:
        print(f"Postgres Error: {e}")
    finally:
        db.close()

    print("\n--- Neo4j Integrity Check ---")
    uri = get_value_from_env("NEO4J_URI", "bolt://neo4j:7687")
    user = get_value_from_env("NEO4J_USERNAME", "neo4j")
    password = get_value_from_env("NEO4J_PASSWORD", "password")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Check for unique patient_ids in Neo4j
            result = session.run("MATCH (n) WHERE n.patient_id IS NOT NULL RETURN DISTINCT n.patient_id as pid")
            neo4j_patient_ids = [record["pid"] for record in result]
            print(f"Patient IDs found in Neo4j: {neo4j_patient_ids}")
            
            if neo4j_patient_ids:
                db = SessionLocal()
                missing_in_pg = []
                for pid in neo4j_patient_ids:
                    p = db.query(Patient).filter(Patient.case_id == pid).first()
                    if not p:
                        missing_in_pg.append(pid)
                db.close()
                
                if missing_in_pg:
                    print(f"CRITICAL: Found {len(missing_in_pg)} Patient IDs in Neo4j that DO NOT exist in Postgres.")
                    for pid in missing_in_pg:
                        print(f" - Missing Patient ID: {pid}")
                else:
                    print("OK: All Patient IDs in Neo4j exist in Postgres.")
            else:
                print("OK: No patient_id properties found in Neo4j.")
                
        driver.close()
    except Exception as e:
        print(f"Neo4j Error: {e}")

if __name__ == "__main__":
    check_integrity()
