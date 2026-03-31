import sys
import os
import shutil
import logging
from sqlalchemy import text

# Add the src directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.database import SessionLocal
from src.main import create_graph_database_connection
from src.entities.user_credential import Neo4jCredentials
from src.shared.env_utils import get_value_from_env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clear_all():
    # 1. Clear Neo4j
    logging.info("Step 1: Clearing Neo4j Knowledge Graph...")
    uri = get_value_from_env("NEO4J_URI")
    username = get_value_from_env("NEO4J_USERNAME")
    password = get_value_from_env("NEO4J_PASSWORD")
    database = get_value_from_env("NEO4J_DATABASE", "neo4j")
    
    if uri and username and password:
        creds = Neo4jCredentials(uri=uri, userName=username, password=password, database=database)
        try:
            graph = create_graph_database_connection(creds)
            graph.query("MATCH (n) DETACH DELETE n")
            logging.info("Neo4j cleared successfully.")
        except Exception as e:
            logging.error(f"Failed to clear Neo4j: {e}")
    else:
        logging.warning("Neo4j credentials or URI missing, skipping Neo4j cleanup.")

    # 2. Clear Postgres
    logging.info("Step 2: Clearing Postgres Clinical Data...")
    try:
        db = SessionLocal()
        # Truncate clinical tables. We keep 'roles', 'users', and 'translation_cache'
        tables_to_clear = [
            "lifestyle_factors", 
            "symptoms", 
            "vitals", 
            "visits", 
            "patients", 
            "user_patient_assignment"
        ]
        truncate_query = f"TRUNCATE TABLE {', '.join(tables_to_clear)} CASCADE"
        db.execute(text(truncate_query))
        db.commit()
        db.close()
        logging.info("Postgres clinical data cleared (CASCADE used).")
    except Exception as e:
        logging.error(f"Failed to clear Postgres: {e}")

    # 3. Clear Patient Files on disk
    logging.info("Step 3: Clearing Patient files on disk...")
    # List all patient directories if possible, or just the specific one
    # For now, targeting the known patient directory
    target_patient = "PT-AP-SANTHO"
    target_path = f"/code/{target_patient}"
    if os.path.exists(target_path):
        shutil.rmtree(target_path, ignore_errors=True)
        logging.info(f"Directory {target_path} removed.")
    else:
        logging.info(f"Directory {target_path} already absent.")

    logging.info("--- SYSTEM RESET COMPLETE ---")

if __name__ == "__main__":
    clear_all()
