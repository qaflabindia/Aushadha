import logging
from datetime import datetime
from src.models import Patient, Visit, Vital, Symptom, LifestyleFactor
from src.database import SessionLocal
from src.llm import extract_structured_ehr_data

class ClinicalService:
    @staticmethod
    async def process_and_persist_ehr(file_name: str, model: str, pages: list, patient_email: str = None):
        """
        Orchestrates structured EHR extraction from document pages and persists to PostgreSQL.
        """
        try:
            logging.info(f"Starting structured EHR extraction for {file_name}")
            full_text = " ".join([page.page_content for page in pages])
            # Limit text to avoid token limits. For extraction of summary EHR, truncated version is usually enough.
            truncated_text = full_text[:15000]
            
            ehr_data = await extract_structured_ehr_data(model, truncated_text)
            
            if not ehr_data:
                logging.warning(f"No EHR data extracted for {file_name}")
                return False

            logging.info(f"Successfully extracted EHR data for {file_name}. Persisting...")
            
            db = SessionLocal()
            try:
                # 1. Patient Upsert
                patient = None
                if patient_email:
                    from src.models import User
                    user = db.query(User).filter(User.email == patient_email).first()
                    if user:
                        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
                        if not patient:
                            patient = Patient(
                                case_id=ehr_data.case_id,
                                user_id=user.id,
                                age_group=ehr_data.age_group,
                                sex=ehr_data.sex
                            )
                            db.add(patient)

                if not patient:
                    patient = db.query(Patient).filter(Patient.case_id == ehr_data.case_id).first()
                if not patient:
                    patient = Patient(
                        case_id=ehr_data.case_id,
                        age_group=ehr_data.age_group,
                        sex=ehr_data.sex
                    )
                    db.add(patient)
                db.commit()
                db.refresh(patient)
                
                # 2. Visit Creation
                visit_date = datetime.now().date()
                if hasattr(ehr_data, 'visit_date') and ehr_data.visit_date != "Unknown":
                    try:
                        visit_date = datetime.strptime(ehr_data.visit_date, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                visit = Visit(
                    patient_id=patient.id,
                    visit_date=visit_date,
                    condition_name=ehr_data.condition_name,
                    chief_complaint=ehr_data.chief_complaint,
                    red_flag_any=ehr_data.red_flag_any,
                    red_flag_details=ehr_data.red_flag_details,
                    bp_category=getattr(ehr_data, 'bp_category', 'Unknown')
                )
                db.add(visit)
                db.commit()
                db.refresh(visit)
                
                # 3. Vitals Persistence
                for v in ehr_data.vitals:
                    vital = Vital(
                        visit_id=visit.id,
                        name=v.name,
                        value=v.value,
                        unit=v.unit,
                        status=v.status
                    )
                    db.add(vital)
                
                # 4. Symptoms Persistence
                for s in ehr_data.symptoms:
                    symptom = Symptom(
                        visit_id=visit.id,
                        name=s.name,
                        status=s.status
                    )
                    db.add(symptom)
                
                # 5. Lifestyle Suspicions (if any)
                if hasattr(ehr_data, 'suspicions'):
                    for susp in ehr_data.suspicions:
                        factor = LifestyleFactor(
                            visit_id=visit.id,
                            name=susp.factor,
                            status=susp.status
                        )
                        db.add(factor)

                db.commit()
                logging.info(f"Structured EHR data persisted for {file_name}")
                return True
            except Exception as persist_err:
                logging.error(f"Error persisting EHR data for {file_name}: {persist_err}")
                db.rollback()
                return False
            finally:
                db.close()
        except Exception as ehr_err:
            logging.error(f"Structured EHR extraction failed for {file_name}: {ehr_err}")
            return False
