
import os
import sys
from langchain_neo4j import Neo4jGraph
from src.shared.common_fn import get_value_from_env

def list_all_neo4j_docs():
    print(f"--- Listing all Neo4j documents ---")
    url = get_value_from_env("NEO4J_URI", "bolt://localhost:7687")
    username = get_value_from_env("NEO4J_USERNAME", "neo4j")
    password = get_value_from_env("NEO4J_PASSWORD", "password")
    database = get_value_from_env("NEO4J_DATABASE", "neo4j")
    
    try:
        graph = Neo4jGraph(url=url, username=username, password=password, database=database)
        
        # List all documents and their patient_id
        q_list = "MATCH (d:Document) RETURN d.fileName as fileName, d.patient_id as patient_id, d.owner_email as owner_email, d.status as status, d.nodeCount as nodeCount"
        res_list = graph.query(q_list)
        print(f"Found {len(res_list)} documents in Neo4j.")
        for r in res_list:
            print(f"  File: {r['fileName']}")
            print(f"    patient_id: {r['patient_id']}")
            print(f"    owner_email: {r['owner_email']}")
            print(f"    status: {r['status']}")
            print(f"    nodeCount: {r['nodeCount']}")

        # Any chunks/entities at all?
        q_chunks = "MATCH (c:Chunk) RETURN count(c) as count"
        res_chunks = graph.query(q_chunks)
        print(f"Total Chunks: {res_chunks[0]['count']}")
        
        q_entities = "MATCH (n) WHERE NOT n:Document AND NOT n:Chunk AND NOT n:Session AND NOT n:`__Community__` RETURN count(n) as count"
        res_entities = graph.query(q_entities)
        print(f"Total Entity/Node Count: {res_entities[0]['count']}")

    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")

if __name__ == "__main__":
    list_all_neo4j_docs()
