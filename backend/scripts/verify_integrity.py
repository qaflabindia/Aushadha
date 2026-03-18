import os
import json
import logging
from langchain_neo4j import Neo4jGraph
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_graph_integrity():
    """
    Diagnostic script to identify nodes and relationships that lack proper patient isolation tags.
    """
    # Load environment variables (ensure they are available in the shell or .env)
    load_dotenv()
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    try:
        graph = Neo4jGraph(url=uri, username=username, password=password, database=database)
        logging.info(f"Connected to Neo4j at {uri} (database: {database})")

        # 1. Check for Documents without patient_email
        orphaned_docs = graph.query("MATCH (d:Document) WHERE d.patient_email IS NULL RETURN d.fileName as fileName")
        if orphaned_docs:
            logging.warning(f"Found {len(orphaned_docs)} Documents without patient_email:")
            for doc in orphaned_docs:
                logging.warning(f"  - {doc['fileName']}")
        else:
            logging.info("No orphaned Document nodes found.")

        # 2. Check for Chunks without patient_email
        orphaned_chunks = graph.query("MATCH (c:Chunk) WHERE c.patient_email IS NULL RETURN count(c) as count")
        if orphaned_chunks[0]['count'] > 0:
            logging.warning(f"Found {orphaned_chunks[0]['count']} Chunks without patient_email.")
        else:
            logging.info("No orphaned Chunk nodes found.")

        # 3. Check for Entity nodes without patient_email (using physical ID check)
        # Note: We rely on the name property or the absence of the 'patient_email' tag
        orphaned_entities = graph.query("""
            MATCH (n) 
            WHERE NOT n:Document AND NOT n:Chunk AND NOT n:_Bloom_Perspective_ AND NOT n:__Community__
            AND (n.patient_email IS NULL OR NOT n.id CONTAINS n.patient_email)
            RETURN labels(n) as labels, n.id as id, n.name as name
            LIMIT 10
        """)
        if orphaned_entities:
            logging.warning(f"Found entities that appear to be un-prefixed or lack patient_email. Sample:")
            for ent in orphaned_entities:
                logging.warning(f"  - Node {ent['labels']} [ID: {ent['id']}, Name: {ent['name']}]")
        else:
            logging.info("Entity nodes appear to be correctly isolated.")

        # 4. Check for relationships without patient_email
        orphaned_rels = graph.query("""
            MATCH ()-[r]->() 
            WHERE r.patient_email IS NULL 
            AND NOT type(r) IN ['PART_OF', 'NEXT_CHUNK', 'HAS_ENTITY', '_Bloom_Perspective_','FIRST_CHUNK','SIMILAR','IN_COMMUNITY','PARENT_COMMUNITY']
            RETURN type(r) as relType, count(r) as count
        """)
        if orphaned_rels:
            logging.warning(f"Found {sum(r['count'] for r in orphaned_rels)} specific domain relationships without patient_email.")
            for r in orphaned_rels:
                logging.warning(f"  - Type: {r['relType']}, Count: {r['count']}")
        else:
            logging.info("All domain relationships appear to be tagged with patient_email.")

    except Exception as e:
        logging.error(f"Integrity check failed: {e}")

if __name__ == "__main__":
    verify_graph_integrity()
