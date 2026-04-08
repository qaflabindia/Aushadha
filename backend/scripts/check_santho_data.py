
import os
import sys
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import User, Patient, Visit, Vital, Symptom, LifestyleFactor, user_patient_association
from langchain_neo4j import Neo4jGraph
from src.shared.common_fn import get_value_from_env

def check_postgres(case_id):
    print(f"--- Checking Postgres for Case ID: {case_id} ---")
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.case_id == case_id).first()
        if not patient:
            print(f"No patient found with Case ID: {case_id}")
            return
        
        print(f"Patient found: ID={patient.id}, Case ID={patient.case_id}, User ID={patient.user_id}")
        
        # If user_id is set, get the user email
        if patient.user_id:
            user = db.query(User).filter(User.id == patient.user_id).first()
            if user:
                print(f"  Linked User Email: {user.email}")
            else:
                print(f"  Linked User ID {patient.user_id} NOT found in Users table!")

        visits = db.query(Visit).filter(Visit.patient_id == patient.id).all()
        print(f"  Number of visits: {len(visits)}")

    finally:
        db.close()

def check_neo4j(patient_id):
    print(f"\n--- Checking Neo4j for Patient ID: {patient_id} ---")
    url = get_value_from_env("NEO4J_URI", "bolt://localhost:7687")
    username = get_value_from_env("NEO4J_USERNAME", "neo4j")
    password = get_value_from_env("NEO4J_PASSWORD", "password")
    database = get_value_from_env("NEO4J_DATABASE", "neo4j")
    
    try:
        graph = Neo4jGraph(url=url, username=username, password=password, database=database)
        
        # Check documents for this patient_id
        q_docs = "MATCH (d:Document {patient_id: $pid}) RETURN d.fileName as fileName, d.status as status"
        res_docs = graph.query(q_docs, {"pid": patient_id})
        print(f"Documents for patient_id {patient_id}: {len(res_docs)}")
        for doc in res_docs:
            print(f"  File: {doc['fileName']}, Status: {doc['status']}")
            
        # Check if there are any chunks/entities for these documents
        q_graph = """
        MATCH (d:Document {patient_id: $pid})<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(n)
        return count(n) as nodeCount
        """
        res_graph = graph.query(q_graph, {"pid": patient_id})
        print(f"Graph nodes (entities) for patient_id {patient_id}: {res_graph[0]['nodeCount']}")

        # Check for PT-AP-SANTHO as both case_id (email) and ID?
        # Sometimes patient_id in Neo4j might be the user's email or something else.
        # Let's check for any mention of PT-AP-SANTHO in any document
        q_any = "MATCH (d:Document) WHERE d.patient_id CONTAINS $pid OR d.owner_email CONTAINS $pid RETURN d.patient_id, d.owner_email, d.fileName"
        res_any = graph.query(q_any, {"pid": patient_id})
        print(f"Other potential matches for '{patient_id}': {len(res_any)}")
        for r in res_any:
            print(f"  Match: patient_id={r['d.patient_id']}, owner_email={r['d.owner_email']}, file={r['d.fileName']}")

    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")

if __name__ == "__main__":
    pid = "PT-AP-SANTHO"
    check_postgres(pid)
    check_neo4j(pid)
