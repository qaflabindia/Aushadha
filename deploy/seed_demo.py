"""Seed the public demo: tables, roles, the admin, a demo patient and judge accounts.

Run inside the backend container (deploy/remote-setup.sh does this):
    ADMIN_EMAIL=<google account> docker exec -i -w /code -e ADMIN_EMAIL backend python - < deploy/seed_demo.py

- ADMIN_EMAIL becomes an Admin who signs in with Google (no password).
- admin@DEMO_DOMAIN: an Admin login with a password, for the presenter.
- One demo patient case (DEMO_CASE_ID) and a Patient login linked to it.
- JUDGE_COUNT Doctor logins, each assigned to the demo patient.

Every run sets fresh random passwords for the demo logins and prints them as
"LOGIN <role> <email> <password>" lines, which deploy.sh saves to a git-ignored file.
"""
import os
import secrets
import sys

import bcrypt

from src.database import Base, SessionLocal, engine
from src.models import Patient, Role, User

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
JUDGE_COUNT = int(os.environ.get("JUDGE_COUNT", "3"))
DEMO_DOMAIN = os.environ.get("DEMO_DOMAIN", "aushadha.demo")
DEMO_CASE_ID = os.environ.get("DEMO_CASE_ID", "PAT-DEMO-HTN")


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _role(db, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        role = Role(name=name)
        db.add(role)
        db.flush()
    return role


def _user(db, email: str, role: Role, password: str | None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
    user.role_id = role.id
    user.hashed_password = _hash(password) if password else None
    db.flush()
    return user


def main() -> int:
    if not ADMIN_EMAIL:
        print("ADMIN_EMAIL is required", file=sys.stderr)
        return 1

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        roles = {name: _role(db, name) for name in ("Admin", "Doctor", "Staff", "Patient")}

        _user(db, ADMIN_EMAIL, roles["Admin"], None)

        patient_email = f"patient.demo@{DEMO_DOMAIN}"
        patient_password = secrets.token_urlsafe(12)
        patient_user = _user(db, patient_email, roles["Patient"], patient_password)
        patient = db.query(Patient).filter(Patient.case_id == DEMO_CASE_ID).first()
        if not patient:
            patient = Patient(case_id=DEMO_CASE_ID, age_group="50-59", sex="Male")
            db.add(patient)
        patient.user_id = patient_user.id
        db.flush()

        # Password admin for the presenter, so a demo never depends on Google sign-in
        admin_demo_email = f"admin@{DEMO_DOMAIN}"
        admin_demo_password = secrets.token_urlsafe(12)
        _user(db, admin_demo_email, roles["Admin"], admin_demo_password)

        logins = [("Admin", admin_demo_email, admin_demo_password), ("Patient", patient_email, patient_password)]
        for n in range(1, JUDGE_COUNT + 1):
            email = f"judge{n}@{DEMO_DOMAIN}"
            password = secrets.token_urlsafe(12)
            judge = _user(db, email, roles["Doctor"], password)
            if patient not in judge.assigned_patients:
                judge.assigned_patients.append(patient)
            logins.append(("Doctor", email, password))

        db.commit()
    finally:
        db.close()

    print(f"CASE {DEMO_CASE_ID}")
    for role, email, password in logins:
        print(f"LOGIN {role} {email} {password}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
