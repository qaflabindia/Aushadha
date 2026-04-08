import logging
import time
from datetime import datetime
from src.shared.env_utils import get_value_from_env
from src.shared.llm_graph_builder_exception import LLMGraphBuilderException
from src.shared.constants import (
    DELETE_ENTITIES_AND_START_FROM_BEGINNING,
    START_FROM_LAST_PROCESSED_POSITION,
    START_FROM_BEGINNING
)

class IngestionService:
    @staticmethod
    async def process_document(credentials, params, pages, merged_file_path=None, is_uploaded_from_local=False):
        """
        Orchestrates the processing of a document: chunking, extraction, and clinical persistence.
        """
        from src.main import (
            create_graph_database_connection, graphDBdataAccess, create_chunk_vector_index,
            get_chunkId_chunkDoc_list, sourceNode, execute_graph_query,
            QUERY_TO_GET_NODES_AND_RELATIONS_OF_A_DOCUMENT, track_token_usage,
            delete_file_from_gcs, delete_uploaded_local_file
        )
        from src.shared.config import GCS_FILE_CACHE, BUCKET_UPLOAD_FILE
        from src.main import create_gcs_bucket_folder_name_hashed
        from src.services.clinical_service import ClinicalService
        from src.services.extraction_service import ExtractionService

        uri_latency = {}
        response = {}
        start_time = datetime.now()
        
        logging.info(f"Starting processing for file: {params.file_name}")
        # 1. Database Connection
        logging.info(f"Connecting to Neo4j database for file: {params.file_name}")
        graph = create_graph_database_connection(credentials)
        graph_db_access = graphDBdataAccess(graph)
        create_chunk_vector_index(graph)

        # 2. Chunking
        logging.info(f"Splitting file into chunks: {params.file_name}")
        total_chunks, chunk_list = get_chunkId_chunkDoc_list(
            graph, params.file_name, pages, params.token_chunk_size, 
            params.chunk_overlap, params.retry_condition, credentials.email, patient_id=params.patient_id
        )
        logging.info(f"File {params.file_name} split into {total_chunks} chunks.")
        uri_latency["total_chunks"] = total_chunks

        # 3. Status Handling (Atomic Test-and-Set)
        # We only allow processing if current status is NOT 'Processing'
        logging.info(f"Attempting to acquire processing lock for: {params.file_name}")
        allowed_from = ['New', 'Completed', 'Failed', 'Cancelled', 'Ready to Reprocess']  # Fix #13: include retry status
        success = graph_db_access.set_status_atomic(
            params.file_name, allowed_from, 'Processing', patient_id=params.patient_id
        )
        
        if not success:
            # Check if it was already processing or if the node is missing
            status_result = graph_db_access.get_current_status_document_node(params.file_name, patient_id=params.patient_id)
            if not status_result:
                 raise LLMGraphBuilderException(f"Document node {params.file_name} not found.")
            
            if status_result[0]['Status'] == 'Processing':
                logging.info(f"File {params.file_name} is already being processed.")
                return uri_latency, response
            else:
                raise LLMGraphBuilderException(f"Failed to acquire processing lock for {params.file_name}.")

        status_result = graph_db_access.get_current_status_document_node(params.file_name, patient_id=params.patient_id)
        if not status_result:
             raise LLMGraphBuilderException("Unable to get the status of document node after locking.")

        # 4. Initialize Processing State
        obj_source_node = sourceNode()
        obj_source_node.file_name = params.file_name
        obj_source_node.status = "Processing"
        obj_source_node.total_chunks = total_chunks
        obj_source_node.model = params.model
        
        node_count = 0
        rel_count = 0
        select_chunks_with_retry = 0
        
        if params.retry_condition == START_FROM_LAST_PROCESSED_POSITION:
            node_count = status_result[0]['nodeCount']
            rel_count = status_result[0]['relationshipCount']
            select_chunks_with_retry = status_result[0]['processed_chunk']
        
        obj_source_node.processed_chunk = select_chunks_with_retry
        obj_source_node.patient_id = params.patient_id
        graph_db_access.update_source_node(obj_source_node)

        # 5. Extraction Loop (Chunks)
        logging.info(f"Starting extraction loop for {params.file_name} using model {params.model}")
        update_batch_size = get_value_from_env("UPDATE_GRAPH_CHUNKS_PROCESSED", 20, "int")
        tokens_per_file = 0
        job_status = "Completed"
        
        for i in range(0, len(chunk_list), update_batch_size):
            # Check for cancellation
            current_status = graph_db_access.get_current_status_document_node(params.file_name, patient_id=params.patient_id)
            if current_status[0]['is_cancelled']:
                job_status = "Cancelled"
                break
            
            batch = chunk_list[i : i + update_batch_size]
            select_upto = i + len(batch)
            
            logging.info(f"Processing batch from chunk {i} to {select_upto} for {params.file_name}")
            node_count, rel_count, latency, tokens = await ExtractionService.process_chunks(
                batch, graph, credentials, params.file_name, params.model,
                params.allowedNodes, params.allowedRelationship, params.chunks_to_combine,
                node_count, rel_count, params.additional_instructions, patient_id=params.patient_id
            )
            
            tokens_per_file += tokens
            logging.info(f"Batch processed. Current node count: {node_count}, rel count: {rel_count}, tokens used so far: {tokens_per_file}")
            
            # Update Progress
            obj_source_node.processed_chunk = select_upto + select_chunks_with_retry
            obj_source_node.token_usage = tokens_per_file
            obj_source_node.node_count = node_count
            obj_source_node.relationship_count = rel_count
            graph_db_access.update_source_node(obj_source_node)

        # 6. Clinical Domain Intelligence — local files only
        # Non-clinical sources (YouTube, web pages, Wikipedia, S3, GCS) must never
        # run through the EHR pipeline or hallucinated data will be persisted to PostgreSQL.
        if params.source_type == 'local file':
            await ClinicalService.process_and_persist_ehr(
                params.file_name, params.model, pages, patient_id=params.patient_id
            )

        # 7. Final Cleanup & Metadata
        if get_value_from_env("TRACK_TOKEN_USAGE", "false", "bool"):
            track_token_usage(credentials.email, credentials.uri, tokens_per_file, params.model)

        total_elapsed = (datetime.now() - start_time).total_seconds()
        
        obj_source_node.status = job_status
        obj_source_node.processing_time = datetime.now() - start_time
        graph_db_access.update_source_node(obj_source_node)
        logging.info(f"Processing finished for {params.file_name} with status: {job_status}")
        
        # Note: final cleanup (deletion) removed per organizational retention policy.

        response.update({
            "fileName": params.file_name,
            "nodeCount": node_count,
            "relationshipCount": rel_count,
            "total_processing_time": round(total_elapsed, 2),
            "status": job_status,
            "model": params.model
        })
        
        return uri_latency, response
