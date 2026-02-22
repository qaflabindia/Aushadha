from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, index=True)
    age_group = Column(String)
    sex = Column(String)

    visits = relationship("Visit", back_populates="patient")

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
