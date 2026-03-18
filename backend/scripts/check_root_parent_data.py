
import os
import sys
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.models import User, Patient, Visit, Vital, Symptom, LifestyleFactor, user_patient_association
from langchain_neo4j import Neo4jGraph
from src.shared.common_fn import get_value_from_env

def check_neo4j_by_email(email):
    print(f"\n--- Checking Neo4j for Email: {email} ---")
    url = get_value_from_env("NEO4J_URI", "bolt://localhost:7687")
    username = get_value_from_env("NEO4J_USERNAME", "neo4j")
    password = get_value_from_env("NEO4J_PASSWORD", "password")
    database = get_value_from_env("NEO4J_DATABASE", "neo4j")
    
    try:
        graph = Neo4jGraph(url=url, username=username, password=password, database=database)
        
        # Check documents for this email as patient_id
        q_patient = "MATCH (d:Document {patient_id: $email}) RETURN d.fileName as fileName, d.status as status"
        res_patient = graph.query(q_patient, {"email": email})
        print(f"Documents for patient_id {email}: {len(res_patient)}")
        for doc in res_patient:
            print(f"  File: {doc['fileName']}, Status: {doc['status']}")
            
        # Check documents for this email as owner_email
        q_owner = "MATCH (d:Document {owner_email: $email}) RETURN d.fileName as fileName, d.status as status, d.patient_id as patient_id"
        res_owner = graph.query(q_owner, {"email": email})
        print(f"Documents owned by {email}: {len(res_owner)}")
        for doc in res_owner:
            print(f"  File: {doc['fileName']}, Status: {doc['status']}, Patient ID: {doc['patient_id']}")
            
        # Check if there are any chunks/entities for these documents
        q_graph = """
        MATCH (d:Document)
        WHERE d.owner_email = $email OR d.patient_id = $email
        MATCH (d)<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(n)
        return count(n) as nodeCount
        """
        res_graph = graph.query(q_graph, {"email": email})
        print(f"Graph nodes (entities) for root.parent@gmail.com: {res_graph[0]['nodeCount']}")

        # Any document at all?
        q_total = "MATCH (d:Document) RETURN count(d) as total"
        res_total = graph.query(q_total)
        print(f"Total documents in Neo4j: {res_total[0]['total']}")

        # List all documents and their patient_id
        q_list = "MATCH (d:Document) RETURN d.fileName as fileName, d.patient_id as patient_id, d.owner_email as owner_email"
        res_list = graph.query(q_list)
        print("List of all documents:")
        for r in res_list:
            print(f"  File: {r['fileName']}, patient_id: {r['patient_id']}, owner_email: {r['owner_email']}")

    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")

if __name__ == "__main__":
    email = "root.parent@gmail.com"
    check_neo4j_by_email(email)
