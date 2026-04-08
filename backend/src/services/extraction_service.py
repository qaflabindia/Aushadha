import logging
import time
from datetime import datetime
from src.shared.common_fn import handle_backticks_nodes_relationship_id_type
from src.shared.env_utils import get_value_from_env

class ExtractionService:
    @staticmethod
    async def process_chunks(chunkId_chunkDoc_list, graph, credentials, file_name, model, 
                             allowedNodes, allowedRelationship, chunks_to_combine, 
                             node_count, rel_count, additional_instructions, patient_id=None):
        """
        Manages the extraction of graph documents from chunks via LLM and saves to Neo4j.
        """
        from src.main import (
            create_chunk_embeddings, get_graph_from_llm, save_graphDocuments_in_neo4j,
            get_chunk_and_graphDocument, merge_relationship_between_chunk_and_entites,
            track_token_usage, graphDBdataAccess
        )

        latency_processing_chunk = {}
        
        # Pre-check token usage allowance
        if get_value_from_env("TRACK_TOKEN_USAGE", "false", "bool"):
            try:
                track_token_usage(credentials.email, credentials.uri, 0, model)
            except Exception as e:
                logging.error(f"Token usage check failed: {e}")
                raise RuntimeError(str(e))
        
        # 1. Update Embeddings
        start_update_embedding = time.time()
        create_chunk_embeddings(graph, chunkId_chunkDoc_list, file_name, patient_id=patient_id)
        latency_processing_chunk["update_embedding"] = f'{time.time() - start_update_embedding:.2f}'
        
        # 2. Extract Entities from LLM
        start_entity_extraction = time.time()
        graph_documents, token_usage = await get_graph_from_llm(
            model, chunkId_chunkDoc_list, allowedNodes, allowedRelationship, 
            chunks_to_combine, additional_instructions
        )
        latency_processing_chunk["entity_extraction"] = f'{time.time() - start_entity_extraction:.2f}'
        
        # 3. Track Token Usage
        if get_value_from_env("TRACK_TOKEN_USAGE", "false", "bool"):
            track_token_usage(credentials.email, credentials.uri, token_usage, model)
        
        # 4. Clean and Save to Neo4j
        cleaned_graph_documents = handle_backticks_nodes_relationship_id_type(graph_documents)
        
        start_save_graphDocuments = time.time()
        save_graphDocuments_in_neo4j(graph, cleaned_graph_documents, patient_id=patient_id)
        latency_processing_chunk["save_graphDocuments"] = f'{time.time() - start_save_graphDocuments:.2f}'

        # 5. Connect Chunks to Entities
        chunks_and_graphDocuments_list = get_chunk_and_graphDocument(cleaned_graph_documents, chunkId_chunkDoc_list)
        
        start_relationship = time.time()
        merge_relationship_between_chunk_and_entites(graph, chunks_and_graphDocuments_list, patient_id=patient_id)
        latency_processing_chunk["relationship_between_chunk_entity"] = f'{time.time() - start_relationship:.2f}'
        
        # 6. Update Counts
        graph_db_access = graphDBdataAccess(graph)
        count_response = graph_db_access.update_node_relationship_count(file_name, patient_id=patient_id)
        new_node_count = count_response[file_name].get('nodeCount', node_count)
        new_rel_count = count_response[file_name].get('relationshipCount', rel_count)
        
        return new_node_count, new_rel_count, latency_processing_chunk, token_usage
