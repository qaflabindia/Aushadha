from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, JSON, Table, DateTime
from sqlalchemy.orm import relationship
import datetime
from .database import Base
from .translation_cache import TranslationCache  # noqa: F401 — ensures table is created

# Association table for Many-to-Many relationship between Doctors/Staff and Patients
user_patient_association = Table(
    'user_patient_assignment', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('patient_id', Integer, ForeignKey('patients.id', ondelete="CASCADE"), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # Admin, Doctor, Staff, Patient

    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)  # Nullable for Google-only users
    role_id = Column(Integer, ForeignKey("roles.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    role = relationship("Role", back_populates="users")
    
    # If the user is a Patient, link to their patient record
    patient_record = relationship("Patient", back_populates="user", uselist=False,
                                  foreign_keys="[Patient.user_id]")
    
    # If the user is a Doctor/Staff, patients assigned to them
    assigned_patients = relationship("Patient", secondary=user_patient_association, 
                                     back_populates="assigned_users")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    age_group = Column(String)
    sex = Column(String)

    user = relationship("User", back_populates="patient_record", foreign_keys=[user_id])
    visits = relationship("Visit", back_populates="patient")
    assigned_users = relationship("User", secondary=user_patient_association, back_populates="assigned_patients")

class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    visit_date = Column(Date)
    condition_name = Column(String)
    chief_complaint = Column(String)
    bp_category = Column(String) # Normal, Elevated, Stage1, Stage2, CrisisSuspected
    red_flag_any = Column(Boolean)
    red_flag_details = Column(JSON) # List of Red Flag IDs: HRF1, HRF2...

    patient = relationship("Patient", back_populates="visits")
    vitals = relationship("Vital", back_populates="visit")
    symptoms = relationship("Symptom", back_populates="visit")
    lifestyle_factors = relationship("LifestyleFactor", back_populates="visit")

class Vital(Base):
    __tablename__ = "vitals"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"))
    name = Column(String)
    value = Column(Float)
    unit = Column(String)
    status = Column(String)

    visit = relationship("Visit", back_populates="vitals")

class Symptom(Base):
    __tablename__ = "symptoms"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"))
    name = Column(String)
    status = Column(String)

    visit = relationship("Visit", back_populates="symptoms")

class LifestyleFactor(Base):
    __tablename__ = "lifestyle_factors"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"))
    name = Column(String)  # High Salt Diet, etc.
    status = Column(String)  # True, False, Unknown

    visit = relationship("Visit", back_populates="lifestyle_factors")
