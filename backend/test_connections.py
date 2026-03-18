import os
import sys
import logging

# Add the /code directory to sys.path to import src modules
sys.path.append('/code')

from src.database import SessionLocal
from src.main import graphDBdataAccess
from langchain_neo4j import Neo4jGraph
from src.shared.env_utils import get_value_from_env

def test_connections():
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Postgres connection...")
    try:
        db = SessionLocal()
        # Simple query to test connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        print("Postgres connection successful.")
        db.close()
    except Exception as e:
        print(f"Postgres connection failed: {e}")

    print("Testing Neo4j connection...")
    try:
        uri = get_value_from_env("NEO4J_URI")
        user = get_value_from_env("NEO4J_USERNAME")
        password = get_value_from_env("NEO4J_PASSWORD")
        database = get_value_from_env("NEO4J_DATABASE", "neo4j")
        
        print(f"Connecting to {uri} (user: {user}, db: {database})")
        graph = Neo4jGraph(url=uri, username=user, password=password, database=database)
        
        # Simple query to test connection
        result = graph.query("MATCH (n) RETURN count(n) as count")
        print(f"Neo4j connection successful. Count: {result[0]['count']}")
        
        # Test get_source_list
        print("Testing get_source_list...")
        da = graphDBdataAccess(graph)
        # Call with 1 argument (patient_id="global")
        sources = da.get_source_list(patient_id="global")
        print(f"get_source_list successful. Found {len(sources)} sources.")
        
    except Exception as e:
        print(f"Neo4j test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connections()
