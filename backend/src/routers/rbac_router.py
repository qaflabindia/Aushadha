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
    case_id: Optional[str] = None  # Only used when role is 'Patient'

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
    
    # 3. Ensure Patient record if role is Patient
    if role.name.upper() == "PATIENT":
        patient_record = db.query(Patient).filter(Patient.user_id == user.id).first()
        if patient_record:
            # Case ID is immutable — reject any attempt to change it
            if request.case_id and request.case_id != patient_record.case_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Case ID '{patient_record.case_id}' is already assigned to this user and cannot be changed."
                )
        else:
            import uuid
            # Use admin-provided Case ID, or auto-generate one
            case_id = (request.case_id.strip() if request.case_id and request.case_id.strip()
                       else f"PAT-{str(uuid.uuid4())[:8].upper()}")
            # Ensure uniqueness
            existing = db.query(Patient).filter(Patient.case_id == case_id).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Case ID '{case_id}' is already in use. Please choose a different one."
                )
            new_patient = Patient(
                case_id=case_id,
                user_id=user.id,
                age_group="Unknown",
                sex="Unknown"
            )
            db.add(new_patient)
            db.commit()

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

@router.get("/users", response_model=List[dict])
async def get_all_users(
    admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin retrieves all registered users and their roles."""
    users = db.query(User).all()
    result = []
    for u in users:
        case_id = None
        if u.role and u.role.name.upper() == "PATIENT":
            patient = db.query(Patient).filter(Patient.user_id == u.id).first()
            case_id = patient.case_id if patient else None
        result.append({
            "id": u.id,
            "email": u.email,
            "role": u.role.name if u.role else "None",
            "case_id": case_id,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    return result

@router.get("/roles", response_model=List[str])
async def get_all_roles(
    admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin retrieves all available role names."""
    roles = db.query(Role).all()
    db_roles = [r.name for r in roles]
    default_roles = ["Admin", "Doctor", "Staff", "Patient"]
    # Return unique roles by converting to a set then back to a list
    return list(set(db_roles + default_roles))

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
        return [{"case_id": p.case_id, "age_group": p.age_group, "sex": p.sex, "email": p.user.email if p.user else None} for p in patients]
        
    elif role == "PATIENT":
        # Patients only see their own linked record
        patient = db.query(Patient).filter(Patient.user_id == db_user.id).first()
        if not patient:
            return []
        return [{"case_id": patient.case_id, "age_group": patient.age_group, "sex": patient.sex, "email": db_user.email}]
        
    elif role in ["DOCTOR", "STAFF"]:
        # Doctors and Staff see assigned records
        patients = db_user.assigned_patients
        return [{"case_id": p.case_id, "age_group": p.age_group, "sex": p.sex, "email": p.user.email if p.user else None} for p in patients]
        
    raise HTTPException(status_code=403, detail="Unknown role")


@router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    admin: AuthenticatedUser = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin deletes a user and their associated patient record."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent self-deletion
    if user.email == admin.email:
        raise HTTPException(status_code=400, detail="Administrators cannot delete themselves.")

    # Associated patient records will be handled by CASCADE/SET NULL in models,
    # but we can explicitly clean up if needed or just let the DB handle it.
    db.delete(user)
    db.commit()
    
    return {"message": f"Successfully deleted user {user.email}"}
