import asyncio
import gc
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request

from src.api_response import create_api_response
from src.database import SessionLocal
from src.entities.user_credential import Neo4jCredentials, get_neo4j_credentials
from src.logger import CustomLogger
from src.main import create_graph_database_connection
from src.models import Patient, Visit, Vital, Symptom, LifestyleFactor
from src.shared.common_fn import formatted_time
from src.shared.google_auth import require_auth, AuthenticatedUser

logger = CustomLogger()
router = APIRouter(tags=["Clinical Intelligence"])


@router.post("/clinical_extraction")
async def extract_clinical_intelligence(
    model: str = Form(...),
    text: str = Form(...),
    condition_profile: str = Form(None),
    user: AuthenticatedUser = Depends(require_auth)
):
    """Extract structured EHR data using profile-aware LLM and clinical validation."""
    try:
        from src.llm import extract_structured_ehr_data, validate_clinical_content

        # 1. Source Gatekeeping
        is_clinical = await validate_clinical_content(model, text)
        if not is_clinical:
            return create_api_response("Failed", message="Non-clinical content detected. This record cannot be processed by the intelligence engine.")

        # 2. LLM Extraction & Intelligence Inference
        result = await extract_structured_ehr_data(model, text, condition_profile)
        if not result:
            return create_api_response("Failed", message="LLM failed to extract/infer structured clinical data.")

        ehr_dict = result.dict()

        # 3. Persistence Hub (Ailment Agnostic)
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.case_id == ehr_dict['case_id']).first()
            if not patient:
                patient = Patient(
                    case_id=ehr_dict['case_id'],
                    age_group=ehr_dict['age_group'],
                    sex=ehr_dict['sex']
                )
                db.add(patient)
                db.flush()

            visit = Visit(
                patient_id=patient.id,
                visit_date=datetime.now().date(),
                condition_name=ehr_dict['condition_name'],
                chief_complaint=ehr_dict['chief_complaint'],
                red_flag_any=ehr_dict['red_flag_any'],
                red_flag_details=ehr_dict['red_flag_list'],
                bp_category=ehr_dict.get('bp_category', 'Unknown')
            )
            db.add(visit)
            db.flush()

            for vit in ehr_dict['vitals']:
                new_vital = Vital(
                    visit_id=visit.id,
                    name=vit['name'],
                    value=vit['value'],
                    unit=vit['unit'],
                    status=vit['status']
                )
                db.add(new_vital)

            for sym in ehr_dict['symptoms']:
                new_sym = Symptom(
                    visit_id=visit.id,
                    name=sym['name'],
                    status=sym['status']
                )
                db.add(new_sym)

            for susp in ehr_dict.get('suspicions', []):
                new_fact = LifestyleFactor(
                    visit_id=visit.id,
                    name=susp['factor'],
                    status=susp['status']
                )
                db.add(new_fact)

            db.commit()
            return create_api_response("Success", data=ehr_dict, message="Clinical record extracted and persisted")
        finally:
            db.close()
    except Exception as e:
        logging.exception("Clinical extraction failed:")
        return create_api_response("Failed", error=str(e))


@router.get("/ehr_data/all")
async def get_all_ehr_data(user: AuthenticatedUser = Depends(require_auth)):
    """Retrieve ALL structured EHR data from PostgreSQL."""
    try:
        db = SessionLocal()
        try:
            visits = db.query(Visit).join(Patient).order_by(Visit.visit_date.desc()).all()

            data = []
            for v in visits:
                record = {
                    "case_id": v.patient.case_id,
                    "visit_date": str(v.visit_date),
                    "age_group": v.patient.age_group,
                    "sex": v.patient.sex,
                    "condition_name": v.condition_name,
                    "chief_complaint": v.chief_complaint,
                    "red_flag_any": v.red_flag_any,
                    "red_flag_details": v.red_flag_details or [],
                    "vitals": [{"name": vit.name, "value": vit.value, "unit": vit.unit, "status": vit.status} for vit in v.vitals],
                    "symptoms": [{"name": sym.name, "status": sym.status} for sym in v.symptoms],
                    "lifestyle_factors": [{"name": lf.name, "status": lf.status} for lf in v.lifestyle_factors]
                }
                data.append(record)

            return create_api_response("Success", data=data)
        finally:
            db.close()
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.get("/ehr_data/{file_name}")
async def get_ehr_data(file_name: str, user: AuthenticatedUser = Depends(require_auth)):
    """Retrieve structured EHR data for a given file name from PostgreSQL."""
    try:
        db = SessionLocal()
        try:
            visits = db.query(Visit).join(Patient).order_by(Visit.visit_date.desc()).all()

            data = []
            for v in visits:
                record = {
                    "case_id": v.patient.case_id,
                    "visit_date": str(v.visit_date),
                    "age_group": v.patient.age_group,
                    "sex": v.patient.sex,
                    "condition_name": v.condition_name,
                    "chief_complaint": v.chief_complaint,
                    "red_flag_any": v.red_flag_any,
                    "red_flag_details": v.red_flag_details or [],
                    "vitals": [{"name": vit.name, "value": vit.value, "unit": vit.unit, "status": vit.status} for vit in v.vitals],
                    "symptoms": [{"name": sym.name, "status": sym.status} for sym in v.symptoms],
                    "lifestyle_factors": [{"name": lf.name, "status": lf.status} for lf in v.lifestyle_factors]
                }
                data.append(record)

            return create_api_response("Success", data=data)
        finally:
            db.close()
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.put("/ehr_data/{case_id}")
async def update_ehr_data(case_id: str, request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Update structured EHR data in PostgreSQL with automated re-validation."""
    try:
        update_data = await request.json()
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.case_id == case_id).first()
            if not patient: return create_api_response("Failed", message="Patient not found")

            if "age_group" in update_data: patient.age_group = update_data["age_group"]
            if "sex" in update_data: patient.sex = update_data["sex"]

            visit = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(Visit.visit_date.desc()).first()
            if visit:
                if "condition_name" in update_data: visit.condition_name = update_data["condition_name"]
                if "chief_complaint" in update_data: visit.chief_complaint = update_data["chief_complaint"]

                if "vitals" in update_data:
                    db.query(Vital).filter(Vital.visit_id == visit.id).delete()
                    for v in update_data["vitals"]:
                        new_vital = Vital(visit_id=visit.id, name=v["name"], value=v["value"], unit=v["unit"], status=v.get("status", "Unknown"))
                        db.add(new_vital)

                if "symptoms" in update_data:
                    db.query(Symptom).filter(Symptom.visit_id == visit.id).delete()
                    for s in update_data["symptoms"]:
                        new_symptom = Symptom(visit_id=visit.id, name=s["name"], status=s["status"])
                        db.add(new_symptom)

                if "lifestyle_factors" in update_data:
                    db.query(LifestyleFactor).filter(LifestyleFactor.visit_id == visit.id).delete()
                    for lf in update_data["lifestyle_factors"]:
                        new_lf = LifestyleFactor(visit_id=visit.id, name=lf["name"], status=lf["status"])
                        db.add(new_lf)

                db.flush()

                # RE-VALIDATION (Intelligence First)
                vitals_text = ", ".join([f"{v.name}: {v.value} {v.unit}" for v in visit.vitals])
                symptoms_text = ", ".join([f"{s.name}: {s.status}" for s in visit.symptoms])
                context_text = f"Condition: {visit.condition_name}. Vitals: {vitals_text}. Symptoms: {symptoms_text}."

                from src.llm import extract_structured_ehr_data
                inference_result = await extract_structured_ehr_data("gpt-4o", context_text, visit.condition_name)

                if inference_result:
                    visit.bp_category = inference_result.dict().get('bp_category', 'Unknown')
                    visit.red_flag_any = inference_result.red_flag_any
                    visit.red_flag_details = inference_result.red_flag_list
                    for v in visit.vitals:
                        match = next((iv for iv in inference_result.vitals if iv.name == v.name), None)
                        if match: v.status = match.status

            db.commit()
            return create_api_response("Success", message=f"Record {case_id} updated and re-validated via Intelligence Engine")
        finally:
            db.close()
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.post("/ehr_data/sync_to_kg")
async def sync_ehr_to_kg(
    case_id: str = Form(...),
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    user: AuthenticatedUser = Depends(require_auth)
):
    """Sync specific clinical record from Postgres to Neo4j including Lifestyle Factors."""
    try:
        db = SessionLocal()
        try:
            patient = db.query(Patient).filter(Patient.case_id == case_id).first()
            if not patient: return create_api_response("Failed", message="Patient not found in Postgres")

            visit = db.query(Visit).filter(Visit.patient_id == patient.id).order_by(Visit.visit_date.desc()).first()
            if not visit: return create_api_response("Failed", message="No visit found for this patient")

            graph = create_graph_database_connection(credentials)

            cypher = """
            MERGE (p:Patient {case_id: $case_id})
            SET p.age_group = $age_group, p.sex = $sex
            MERGE (v:Visit {case_id: $case_id, visit_date: $visit_date})
            SET v.condition_name = $condition_name, v.chief_complaint = $chief_complaint,
                v.red_flag_any = $red_flag_any, v.red_flag_details = $red_flag_details,
                v.bp_category = $bp_category
            MERGE (p)-[:HAS_VISIT]->(v)
            WITH v
            OPTIONAL MATCH (v)-[r:HAS_VITAL|HAS_SYMPTOM|HAS_LIFESTYLE]->(e)
            DELETE r, e
            """
            graph.query(cypher, params={
                "case_id": patient.case_id, "age_group": patient.age_group, "sex": patient.sex,
                "visit_date": str(visit.visit_date), "condition_name": visit.condition_name,
                "chief_complaint": visit.chief_complaint, "red_flag_any": visit.red_flag_any,
                "red_flag_details": visit.red_flag_details or [],
                "bp_category": visit.bp_category or "Unknown"
            })

            for vit in visit.vitals:
                graph.query("MATCH (v:Visit {case_id: $case_id, visit_date: $visit_date}) "
                            "CREATE (vit:Vital {name: $name, value: $value, unit: $unit, status: $status}) "
                            "CREATE (v)-[:HAS_VITAL]->(vit)",
                            params={"case_id": patient.case_id, "visit_date": str(visit.visit_date),
                                    "name": vit.name, "value": vit.value, "unit": vit.unit, "status": vit.status})

            for sym in visit.symptoms:
                graph.query("MATCH (v:Visit {case_id: $case_id, visit_date: $visit_date}) "
                            "CREATE (s:Symptom {name: $name, status: $status}) "
                            "CREATE (v)-[:HAS_SYMPTOM]->(s)",
                            params={"case_id": patient.case_id, "visit_date": str(visit.visit_date),
                                    "name": sym.name, "status": sym.status})

            for lf in visit.lifestyle_factors:
                graph.query("MATCH (v:Visit {case_id: $case_id, visit_date: $visit_date}) "
                            "CREATE (l:LifestyleFactor {name: $name, status: $status}) "
                            "CREATE (v)-[:HAS_LIFESTYLE]->(l)",
                            params={"case_id": patient.case_id, "visit_date": str(visit.visit_date),
                                    "name": lf.name, "status": lf.status})

            return create_api_response("Success", message=f"Record {case_id} synchronized to Knowledge Graph")
        finally:
            db.close()
    except Exception as e:
        return create_api_response("Failed", error=str(e))
