import os
import logging
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text
# Using the project's standard environment utility which prioritizes the Secret Vault
from src.shared.env_utils import get_value_from_env
from src.shared.secret_vault import get_secret

logging.basicConfig(level=logging.INFO)

def check_vault_status():
    print("--- Secret Vault Status ---")
    master_pwd = os.getenv("VAULT_MASTER_PASSWORD")
    key_file = os.path.exists("/code/.vault.key")
    print(f"VAULT_MASTER_PASSWORD set: {bool(master_pwd)}")
    print(f"Vault key file exists: {key_file} (/code/.vault.key)")
    
    # Check if we can retrieve a known secret (e.g., NEO4J_PASSWORD)
    pwd = get_secret("NEO4J_PASSWORD")
    print(f"Can retrieve NEO4J_PASSWORD from vault: {bool(pwd)}")

def check_neo4j():
    print("\n--- Neo4j Check (Secure Architecture) ---")
    # Using get_value_from_env which handles Vault -> Environment fallback
    uri = get_value_from_env("NEO4J_URI", "bolt://neo4j:7687")
    user = get_value_from_env("NEO4J_USERNAME", "neo4j")
    password = get_value_from_env("NEO4J_PASSWORD", "password")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"Total Nodes: {count}")
            
            # Checking for Document and Chunk nodes as per Aushadha spec
            result = session.run("MATCH (d:Document) RETURN d.fileName as fileName LIMIT 5")
            docs = [record["fileName"] for record in result]
            print(f"Sample Documents: {docs}")
            
            result = session.run("MATCH (c:Chunk) RETURN count(c) as count")
            chunk_count = result.single()["count"]
            print(f"Total Chunks: {chunk_count}")
        driver.close()
    except Exception as e:
        print(f"Neo4j Error: {e}")

def check_postgres():
    print("\n--- Postgres Check (Aushadha Patient Registry) ---")
    user = get_value_from_env("POSTGRES_USER", "aushadha_user")
    password = get_value_from_env("POSTGRES_PASSWORD", "aushadha_secure_db_2026")
    host = get_value_from_env("POSTGRES_HOST", "postgres")
    port = get_value_from_env("POSTGRES_PORT", "5432")
    db = get_value_from_env("POSTGRES_DB", "aushadha")
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            # Check public schema tables (Registry, EHR data)
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [row[0] for row in result]
            print(f"Tables: {tables}")
            
            # Check for Patient data if exists
            if "patients" in tables:
                result = conn.execute(text("SELECT count(*) FROM patients"))
                count = result.scalar()
                print(f"Total Patients: {count}")
    except Exception as e:
        print(f"Postgres Error: {e}")

if __name__ == "__main__":
    check_vault_status()
    check_neo4j()
    check_postgres()
