from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from src.database import get_db
from src.models import User, Role, Patient
from src.shared.google_auth import require_auth, AuthenticatedUser
from src.routers.admin_router import require_admin

router = APIRouter(tags=["RBAC"], prefix="/rbac")

class RoleAssignRequest(BaseModel):
    email: str
    role_name: str

class PatientAssignRequest(BaseModel):
    doctor_email: str
    patient_case_id: str

@router.post("/assign_role")
async def assign_role(
    request: RoleAssignRequest,
    admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin assigns a role (Admin, Doctor, Staff, Patient) to a user."""
    role_name = request.role_name.capitalize()
    
    # 1. Ensure the Role exists
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name)
        db.add(role)
        db.commit()
        db.refresh(role)
        
    # 2. Find or Create User
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        user = User(email=request.email, role_id=role.id)
        db.add(user)
    else:
        user.role_id = role.id

    db.commit()
    db.refresh(user)
    return {"message": f"Assigned role {role.name} to {user.email}"}


@router.post("/assign_patient")
async def assign_patient(
    request: PatientAssignRequest,
    admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin assigns a Doctor or Staff member to a Patient record."""
    user = db.query(User).filter(User.email == request.doctor_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Doctor/Staff user not found")
        
    if user.role and user.role.name not in ["Doctor", "Staff", "Admin"]:
        raise HTTPException(status_code=400, detail="Can only assign patients to Doctor, Staff, or Admin")
        
    patient = db.query(Patient).filter(Patient.case_id == request.patient_case_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found")
        
    # Assign
    if patient not in user.assigned_patients:
        user.assigned_patients.append(patient)
        db.commit()
        
    return {"message": f"Assigned patient {patient.case_id} to {user.email}"}

@router.get("/my_patients")
async def get_my_patients(
    current_user: AuthenticatedUser = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Retrieve patients accessible by the current user based on RBAC."""
    db_user = db.query(User).filter(User.email == current_user.email).first()
    if not db_user or not db_user.role:
        raise HTTPException(status_code=403, detail="Unregistered user or role missing")
        
    role = db_user.role.name.upper()
    
    if role == "ADMIN":
        # Admins see everything
        patients = db.query(Patient).all()
        return [{"case_id": p.case_id, "age_group": p.age_group, "sex": p.sex} for p in patients]
        
    elif role == "PATIENT":
        # Patients only see their own linked record
        patient = db.query(Patient).filter(Patient.user_id == db_user.id).first()
        if not patient:
            return []
        return [{"case_id": patient.case_id, "age_group": patient.age_group, "sex": patient.sex}]
        
    elif role in ["DOCTOR", "STAFF"]:
        # Doctors and Staff see assigned records
        patients = db_user.assigned_patients
        return [{"case_id": p.case_id, "age_group": p.age_group, "sex": p.sex} for p in patients]
        
    raise HTTPException(status_code=403, detail="Unknown role")
