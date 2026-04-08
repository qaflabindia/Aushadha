import asyncio
import logging
import os
import sys
from datetime import datetime

# IMPORTANT: Set this BEFORE importing any src modules that might use it
os.environ["MAX_CONCURRENT_LLM_CALLS"] = "1"

# Add the src directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.shared.env_utils import get_value_from_env
from src.entities.user_credential import Neo4jCredentials
from src.entities.source_extract_params import SourceScanExtractParams
from src.entities.source_node import sourceNode
from src.graphDB_dataAccess import graphDBdataAccess
from src.main import extract_graph_from_file_local_file, create_graph_database_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def reindex_files():
    patient_id = "PT-AP-SANTHO"
    email = "lakshminarasimhan.santhanam@gigkri.com"
    model = "openai_gpt_4o"
    
    # 1. Get Credentials from Vault/Env
    uri = get_value_from_env("NEO4J_URI")
    username = get_value_from_env("NEO4J_USERNAME")
    password = get_value_from_env("NEO4J_PASSWORD")
    database = get_value_from_env("NEO4J_DATABASE", "neo4j")
    
    if not uri:
        logging.error("NEO4J_URI is missing.")
        return

    credentials = Neo4jCredentials(
        uri=uri,
        userName=username,
        password=password,
        database=database,
        email=email,
        user_role="Admin"
    )
    
    # 2. List files to index
    merged_dir = f"/code/{patient_id}/merged_files"
    if not os.path.exists(merged_dir):
        logging.error(f"Directory not found: {merged_dir}")
        return

    files = [f for f in os.listdir(merged_dir) if f.endswith('.pdf')]
    logging.info(f"Found {len(files)} files to re-index for patient {patient_id}")

    # 3. Initialize Graph Connection
    graph = create_graph_database_connection(credentials)
    graph_db_access = graphDBdataAccess(graph)

    for file_name in sorted(files):
        logging.info(f"--- Processing: {file_name} ---")
        
        # A. Create/Merge Source Node in Neo4j
        obj_source_node = sourceNode()
        obj_source_node.file_name = file_name
        obj_source_node.file_size = os.path.getsize(os.path.join(merged_dir, file_name))
        obj_source_node.file_type = "pdf"
        obj_source_node.file_source = "local file"
        obj_source_node.model = model
        obj_source_node.created_at = datetime.now()
        obj_source_node.patient_id = patient_id
        obj_source_node.chunkNodeCount = 0
        obj_source_node.chunkRelCount = 0
        obj_source_node.entityNodeCount = 0
        obj_source_node.entityEntityRelCount = 0
        obj_source_node.communityNodeCount = 0
        obj_source_node.communityRelCount = 0
        
        logging.info(f"Ensuring Document node exists for {file_name}")
        graph_db_access.create_source_node(obj_source_node)

        # B. Trigger Extraction
        params = SourceScanExtractParams(
            model=model,
            file_name=file_name,
            source_type="local file",
            patient_id=patient_id,
            token_chunk_size=1000,
            chunk_overlap=50,
            chunks_to_combine=1 # FIX: Must not be None
        )
        
        merged_file_path = os.path.join(merged_dir, file_name)
        
        try:
            logging.info(f"Starting extraction for {file_name}")
            latency, result = await extract_graph_from_file_local_file(credentials, params, merged_file_path)
            logging.info(f"Successfully indexed {file_name}")
        except Exception as e:
            logging.error(f"Failed to index {file_name}: {e}")

if __name__ == "__main__":
    asyncio.run(reindex_files())
