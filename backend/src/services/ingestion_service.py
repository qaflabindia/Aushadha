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
            GCS_FILE_CACHE, BUCKET_UPLOAD_FILE, create_gcs_bucket_folder_name_hashed,
            delete_file_from_gcs, delete_uploaded_local_file
        )
        from src.services.clinical_service import ClinicalService
        from src.services.extraction_service import ExtractionService

        uri_latency = {}
        response = {}
        start_time = datetime.now()
        
        # 1. Database Connection
        graph = create_graph_database_connection(credentials)
        graph_db_access = graphDBdataAccess(graph)
        create_chunk_vector_index(graph)

        # 2. Chunking
        total_chunks, chunk_list = get_chunkId_chunkDoc_list(
            graph, params.file_name, pages, params.token_chunk_size, 
            params.chunk_overlap, params.retry_condition, credentials.email
        )
        uri_latency["total_chunks"] = total_chunks

        # 3. Status Handling
        status_result = graph_db_access.get_current_status_document_node(params.file_name, credentials.email)
        if not status_result:
             raise LLMGraphBuilderException("Unable to get the status of document node.")
        
        if status_result[0]['Status'] == 'Processing':
            logging.info(f"File {params.file_name} is already being processed.")
            return uri_latency, response

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
        graph_db_access.update_source_node(obj_source_node)

        # 5. Extraction Loop (Chunks)
        update_batch_size = get_value_from_env("UPDATE_GRAPH_CHUNKS_PROCESSED", 20, "int")
        tokens_per_file = 0
        job_status = "Completed"
        
        for i in range(0, len(chunk_list), update_batch_size):
            # Check for cancellation
            current_status = graph_db_access.get_current_status_document_node(params.file_name, credentials.email)
            if current_status[0]['is_cancelled']:
                job_status = "Cancelled"
                break
            
            batch = chunk_list[i : i + update_batch_size]
            select_upto = i + len(batch)
            
            node_count, rel_count, latency, tokens = await ExtractionService.process_chunks(
                batch, graph, credentials, params.file_name, params.model,
                params.allowedNodes, params.allowedRelationship, params.chunks_to_combine,
                node_count, rel_count, params.additional_instructions
            )
            
            tokens_per_file += tokens
            
            # Update Progress
            obj_source_node.processed_chunk = select_upto + select_chunks_with_retry
            obj_source_node.token_usage = tokens_per_file
            obj_source_node.node_count = node_count
            obj_source_node.relationship_count = rel_count
            graph_db_access.update_source_node(obj_source_node)

        # 6. Clinical Domain Intelligence (Refactored)
        await ClinicalService.process_and_persist_ehr(params.file_name, params.model, pages, patient_email=params.patient_email)

        # 7. Final Cleanup & Metadata
        if get_value_from_env("TRACK_TOKEN_USAGE", "false", "bool"):
            track_token_usage(credentials.email, credentials.uri, tokens_per_file, params.model)

        total_elapsed = (datetime.now() - start_time).total_seconds()
        
        obj_source_node.status = job_status
        obj_source_node.processing_time = datetime.now() - start_time
        graph_db_access.update_source_node(obj_source_node)
        
        if is_uploaded_from_local and job_status != "Cancelled":
            if GCS_FILE_CACHE:
                folder = create_gcs_bucket_folder_name_hashed(credentials.uri, params.file_name)
                delete_file_from_gcs(BUCKET_UPLOAD_FILE, folder, params.file_name)
            else:
                delete_uploaded_local_file(merged_file_path, params.file_name)

        response.update({
            "fileName": params.file_name,
            "nodeCount": node_count,
            "relationshipCount": rel_count,
            "total_processing_time": round(total_elapsed, 2),
            "status": job_status,
            "model": params.model
        })
        
        return uri_latency, response
