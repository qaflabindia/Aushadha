import asyncio
import base64
import gc
import json
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from google.oauth2.credentials import Credentials
from langchain_neo4j import Neo4jGraph
from sse_starlette.sse import EventSourceResponse

from src.api_response import create_api_response
from src.communities import create_communities
from src.entities.source_extract_params import SourceScanExtractParams, get_source_scan_extract_params
from src.entities.user_credential import Neo4jCredentials, get_neo4j_credentials
from src.graphDB_dataAccess import graphDBdataAccess
from src.graph_query import visualize_schema
from src.logger import CustomLogger
from src.main import (
    connection_check_and_get_vector_dimensions, create_source_node_graph_url_gcs, create_source_node_graph_url_s3,
    create_source_node_graph_url_youtube, create_source_node_graph_web_url,
    create_graph_database_connection, create_source_node_graph_url_wikipedia,
    extract_graph_from_file_Wikipedia, extract_graph_from_file_gcs,
    extract_graph_from_file_local_file, extract_graph_from_file_s3, extract_graph_from_file_youtube,
    extract_graph_from_web_page, failed_file_process, get_labels_and_relationtypes, get_source_list_from_graph,
    manually_cancelled_job, populate_graph_schema_from_text, set_status_retry, update_graph, upload_file
)
from src.post_processing import create_entity_embedding, create_vector_fulltext_indexes, graph_schema_consolidation
from src.shared.common_fn import formatted_time
from src.shared.env_utils import get_value_from_env
from src.shared.llm_graph_builder_exception import LLMGraphBuilderException

logger = CustomLogger()
CHUNK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chunks")
MERGED_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "merged_files")

router = APIRouter(tags=["Graph & Extraction"])


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent directory traversal."""
    return os.path.basename(filename)


def validate_file_path(directory: str, filename: str) -> str:
    """Validate that the file path is within the given directory."""
    filepath = os.path.join(directory, filename)
    abs_dir = os.path.abspath(directory)
    abs_file = os.path.abspath(filepath)
    if not abs_file.startswith(abs_dir):
        raise ValueError(f"Invalid file path: {filename}")
    return abs_file


def decode_password(pwd):
    return base64.b64decode(pwd).decode("utf-8")


# ---------------------------------------------------------------------------
# Connection & Schema
# ---------------------------------------------------------------------------

@router.post("/connect")
async def connect(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """Connect to the Neo4j database and check vector dimensions."""
    try:
        start = time.time()
        if credentials.uri:
            uri = credentials.uri.lower()
            if 'localhost' in uri or '127.0.0.1' in uri:
                new_uri = credentials.uri.replace('localhost', 'neo4j').replace('127.0.0.1', 'neo4j')
                logging.info(f"Mapping {credentials.uri} to {new_uri} for Docker-side connection")
                credentials.uri = new_uri
            if not (credentials.uri.startswith('bolt://') or
                    credentials.uri.startswith('neo4j://') or
                    credentials.uri.startswith('bolt+s://') or
                    credentials.uri.startswith('neo4j+s://')):
                credentials.uri = f"bolt://{credentials.uri}"

        logging.info(f"Final URI for connection attempt: {credentials.uri}")
        graph = create_graph_database_connection(credentials)

        logging.info(f"Connection created, checking dimensions for database: {credentials.database}")
        result = await asyncio.to_thread(connection_check_and_get_vector_dimensions, graph, credentials.database)
        logging.info(f"Dimensions check result: {result}")
        gcs_cache = get_value_from_env("GCS_FILE_CACHE","False","bool")
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'connect','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'count':1, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        result['elapsed_api_time'] = f'{elapsed_time:.2f}'
        result['gcs_file_cache'] = gcs_cache
        return create_api_response('Success',data=result)
    except Exception as e:
        job_status = "Failed"
        message="Connection failed to connect Neo4j database"
        error_message = str(e)
        logging.exception(f'Connection failed to connect Neo4j database:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)

@router.post("/backend_connection_configuration")
async def backend_connection_configuration():
    try:
        start = time.time()
        uri = get_value_from_env("NEO4J_URI")
        username= get_value_from_env("NEO4J_USERNAME")
        database= get_value_from_env("NEO4J_DATABASE")
        password= get_value_from_env("NEO4J_PASSWORD")
        gcs_cache = get_value_from_env("GCS_FILE_CACHE","False","bool")
        if all([uri, username, database, password]):
            graph = Neo4jGraph()
            logging.info(f'login connection status of object: {graph}')
            if graph is not None:
                graph_connection = True
                temp_credentials = Neo4jCredentials(uri=uri, userName=username, password=password, database=database)

                logging.info(f"Final URI for connection attempt: {temp_credentials.uri}")
                graph = create_graph_database_connection(temp_credentials)

                logging.info(f"Connection created, checking dimensions for database: {temp_credentials.database}")
                result = await asyncio.to_thread(connection_check_and_get_vector_dimensions, graph, temp_credentials.database)
                logging.info(f"Dimensions check result: {result}")

                result['gcs_file_cache'] = gcs_cache
                result['uri'] = uri
                end = time.time()
                elapsed_time = end - start
                result['api_name'] = 'backend_connection_configuration'
                result['elapsed_api_time'] = f'{elapsed_time:.2f}'
                result['graph_connection'] = f'{graph_connection}',
                result['connection_from'] = 'backendAPI'
                logger.log_struct(result, "INFO")
                return create_api_response('Success',message=f"Backend connection successful",data=result)
        else:
            graph_connection = False
            return create_api_response('Success',message=f"Backend connection is not successful",data=graph_connection)
    except Exception as e:
        graph_connection = False
        job_status = "Failed"
        message="Unable to connect backend DB"
        error_message = str(e)
        logging.exception(f'{error_message}')
        return create_api_response(job_status, message=message, error=error_message.rstrip('.') + ', or fill from the login dialog.', data=graph_connection)
    finally:
        gc.collect()


# ---------------------------------------------------------------------------
# Source URL Scan & Upload
# ---------------------------------------------------------------------------

@router.post("/url/scan")
async def create_source_knowledge_graph_url(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    params: SourceScanExtractParams = Depends(get_source_scan_extract_params)
):
    """Create a source node in the knowledge graph from a given URL or bucket."""
    try:
        start = time.time()
        source = params.source_url if params.source_url is not None else params.wiki_query
        graph = create_graph_database_connection(credentials)
        if params.source_type == 's3 bucket' and params.aws_access_key_id and params.aws_secret_access_key:
            lst_file_name, success_count, failed_count = await asyncio.to_thread(create_source_node_graph_url_s3, graph, params)
        elif params.source_type == 'gcs bucket':
            lst_file_name, success_count, failed_count = create_source_node_graph_url_gcs(
                graph, params, Credentials(params.access_token)
            )
        elif params.source_type == 'web-url':
            lst_file_name, success_count, failed_count = await asyncio.to_thread(
                create_source_node_graph_web_url, graph, params)
        elif params.source_type == 'youtube':
            lst_file_name, success_count, failed_count = await asyncio.to_thread(
                create_source_node_graph_url_youtube, graph, params)
        elif params.source_type == 'Wikipedia':
            lst_file_name, success_count, failed_count = await asyncio.to_thread(
                create_source_node_graph_url_wikipedia, graph, params)
        else:
            return create_api_response('Failed', message='source_type is other than accepted source')

        message = f"Source Node created successfully for source type: {params.source_type} and source: {source}"
        end = time.time()
        elapsed_time = end - start
        json_obj = {
            'api_name': 'url_scan', 'db_url': credentials.uri, 'url_scanned_file': lst_file_name,
            'source_url': params.source_url, 'wiki_query': params.wiki_query,
            'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time': f'{elapsed_time:.2f}',
            'userName': credentials.userName, 'database': credentials.database,
            'aws_access_key_id': params.aws_access_key_id, 'model': params.model,
            'gcs_bucket_name': params.gcs_bucket_name, 'gcs_bucket_folder': params.gcs_bucket_folder,
            'source_type': params.source_type, 'gcs_project_id': params.gcs_project_id, 'email': credentials.email
        }
        logger.log_struct(json_obj, "INFO")
        result = {'elapsed_api_time': f'{elapsed_time:.2f}'}
        return create_api_response("Success", message=message, success_count=success_count, failed_count=failed_count, file_name=lst_file_name, data=result)
    except LLMGraphBuilderException as e:
        error_message = str(e)
        message = f" Unable to create source node for source type: {params.source_type} and source: {source}"
        json_obj = {'error_message':error_message, 'status':'Success','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,'success_count':1, 'source_type': params.source_type, 'source_url':params.source_url, 'wiki_query':params.wiki_query, 'logging_time': formatted_time(datetime.now(timezone.utc)),'email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        logging.exception(f'File Failed in upload: {e}')
        return create_api_response('Failed',message=message + error_message[:80],error=error_message,file_source=params.source_type)
    except Exception as e:
        error_message = str(e)
        message = f" Unable to create source node for source type: {params.source_type} and source: {source}"
        json_obj = {'error_message':error_message, 'status':'Failed','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,'failed_count':1, 'source_type': params.source_type, 'source_url':params.source_url, 'wiki_query':params.wiki_query, 'logging_time': formatted_time(datetime.now(timezone.utc)),'email':credentials.email}
        logger.log_struct(json_obj, "ERROR")
        logging.exception(f'Exception Stack trace upload:{e}')
        return create_api_response('Failed',message=message + error_message[:80],error=error_message,file_source=params.source_type)
    finally:
        gc.collect()

@router.post("/upload")
async def upload_large_file_into_chunks(
    file: UploadFile = File(...),
    chunkNumber=Form(None),
    totalChunks=Form(None),
    originalname=Form(None),
    model=Form(None),
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials)
):
    """Upload a large file in chunks and create a source node."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        result = await asyncio.to_thread(upload_file, graph, model, file, chunkNumber, totalChunks, originalname, credentials.uri, CHUNK_DIR, MERGED_DIR, credentials.email)
        end = time.time()
        elapsed_time = end - start
        if int(chunkNumber) == int(totalChunks):
            json_obj = {'api_name':'upload','db_url':credentials.uri,'userName':credentials.userName, 'database':credentials.database, 'chunkNumber':chunkNumber,'totalChunks':totalChunks,
                                'filename':originalname,'model':model, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
            logger.log_struct(json_obj, "INFO")
            print("upload log obj",json_obj)
        if int(chunkNumber) == int(totalChunks):
            return create_api_response('Success',data=result, message='Source Node Created Successfully')
        else:
            return create_api_response('Success', message=result)
    except Exception as e:
        message="Unable to upload file in chunks"
        error_message = str(e)
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        graphDb_data_Access.update_exception_db(originalname,error_message)
        logging.info(message)
        logging.exception(f'Exception:{error_message}')
        return create_api_response('Failed', message=message + error_message[:100], error=error_message, file_name = originalname)
    finally:
        gc.collect()


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

@router.post("/extract")
async def extract_knowledge_graph_from_file(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    params: SourceScanExtractParams = Depends(get_source_scan_extract_params)
):
    """Extract a knowledge graph from a file or URL source."""
    try:
        start_time = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)

        if params.source_type == 'local file':
            file_name = sanitize_filename(params.file_name)
            params.file_name = file_name
            merged_file_path = validate_file_path(MERGED_DIR, file_name)
            uri_latency, result = await extract_graph_from_file_local_file(credentials, params, merged_file_path)
        elif params.source_type == 's3 bucket' and params.source_url:
            uri_latency, result = await extract_graph_from_file_s3(credentials, params)
        elif params.source_type == 'web-url':
            uri_latency, result = await extract_graph_from_web_page(credentials, params)
        elif params.source_type == 'youtube' and params.source_url:
            uri_latency, result = await extract_graph_from_file_youtube(credentials, params)
        elif params.source_type == 'Wikipedia' and params.wiki_query:
            uri_latency, result = await extract_graph_from_file_Wikipedia(credentials, params)
        elif params.source_type == 'gcs bucket' and params.gcs_bucket_name:
            uri_latency, result = await extract_graph_from_file_gcs(credentials, params)
        else:
            return create_api_response('Failed', message='source_type is other than accepted source')
        extract_api_time = time.time() - start_time
        json_obj = result.copy()
        if result is not None:
            logging.info("Going for counting nodes and relationships in extract")
            count_node_time = time.time()
            graph = create_graph_database_connection(credentials)
            graphDb_data_Access = graphDBdataAccess(graph)
            count_response = graphDb_data_Access.update_node_relationship_count(params.file_name)
            logging.info("Nodes and Relationship Counts updated")
            if count_response :
                result['chunkNodeCount'] = count_response[params.file_name].get('chunkNodeCount',"0")
                result['chunkRelCount'] =  count_response[params.file_name].get('chunkRelCount',"0")
                result['entityNodeCount']=  count_response[params.file_name].get('entityNodeCount',"0")
                result['entityEntityRelCount']=  count_response[params.file_name].get('entityEntityRelCount',"0")
                result['communityNodeCount']=  count_response[params.file_name].get('communityNodeCount',"0")
                result['communityRelCount']= count_response[params.file_name].get('communityRelCount',"0")
                result['nodeCount'] = count_response[params.file_name].get('nodeCount',"0")
                result['relationshipCount']  = count_response[params.file_name].get('relationshipCount',"0")
                logging.info(f"counting completed in {(time.time()-count_node_time):.2f}")

            json_obj['db_url'] = credentials.uri
            json_obj['api_name'] = 'extract'
            json_obj['source_url'] = params.source_url
            json_obj['wiki_query'] = params.wiki_query
            json_obj['source_type'] = params.source_type
            json_obj['logging_time'] = formatted_time(datetime.now(timezone.utc))
            json_obj['elapsed_api_time'] = f'{extract_api_time:.2f}'
            json_obj['userName'] = credentials.userName
            json_obj['database'] = credentials.database
            json_obj['email'] = credentials.email
        logger.log_struct(json_obj, "INFO")
        result.update(uri_latency)
        logging.info(f"extraction completed in {extract_api_time:.2f} seconds for file name {params.file_name}")
        return create_api_response('Success', data=result, file_source= params.source_type)
    except LLMGraphBuilderException as e:
        error_message = str(e)
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        graphDb_data_Access.update_exception_db(params.file_name,error_message, params.retry_condition)
        if params.source_type == 'local file':
            failed_file_process(credentials.uri,params.file_name, merged_file_path)
        node_detail = graphDb_data_Access.get_current_status_document_node(params.file_name)
        json_obj = {'api_name':'extract','message':error_message,'file_created_at':formatted_time(node_detail[0]['created_time']),'error_message':error_message, 'filename': params.file_name,'status':'Completed',
                    'db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,'failed_count':1, 'source_type': params.source_type, 'source_url':params.source_url, 'wiki_query':params.wiki_query, 'logging_time': formatted_time(datetime.now(timezone.utc)),'email':credentials.email}
        logger.log_struct(json_obj, "ERROR")
        logging.exception(f'File Failed in extraction: {e}')
        return create_api_response("Failed", message = error_message, error=error_message, file_name=params.file_name)
    except Exception as e:
        message=f"Failed To Process File:{params.file_name} or LLM Unable To Parse Content "
        error_message = str(e)
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        graphDb_data_Access.update_exception_db(params.file_name,error_message, params.retry_condition)
        if params.source_type == 'local file':
            failed_file_process(credentials.uri,params.file_name, merged_file_path)
        node_detail = graphDb_data_Access.get_current_status_document_node(params.file_name)

        json_obj = {'api_name':'extract','message':message,'file_created_at':formatted_time(node_detail[0]['created_time']),'error_message':error_message, 'filename': params.file_name,'status':'Failed',
                    'db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,'failed_count':1, 'source_type': params.source_type, 'source_url':params.source_url, 'wiki_query':params.wiki_query, 'logging_time': formatted_time(datetime.now(timezone.utc)),'email':credentials.email}
        logger.log_struct(json_obj, "ERROR")
        logging.exception(f'File Failed in extraction: {e}')
        return create_api_response('Failed', message=message + error_message[:100], error=error_message, file_name = params.file_name)
    finally:
        gc.collect()


# ---------------------------------------------------------------------------
# Source & Schema Queries
# ---------------------------------------------------------------------------

@router.post("/sources_list")
async def get_source_list(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """Get the list of sources already present in the database."""
    try:
        start = time.time()
        result = await asyncio.to_thread(get_source_list_from_graph,credentials)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'sources_list','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response("Success",data=result, message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        job_status = "Failed"
        message="Unable to fetch source list"
        error_message = str(e)
        logging.exception(f'Exception:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)

@router.post("/schema")
async def get_structured_schema(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """Get the structured schema (labels and relation types) from Neo4j."""
    try:
        start = time.time()
        result = await asyncio.to_thread(get_labels_and_relationtypes, credentials)
        end = time.time()
        elapsed_time = end - start
        logging.info(f'Schema result from DB: {result}')
        json_obj = {'api_name':'schema','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success', data=result,message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        message="Unable to get the labels and relationtypes from neo4j database"
        error_message = str(e)
        logging.info(message)
        logging.exception(f'Exception:{error_message}')
        return create_api_response("Failed", message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/schema_visualization")
async def get_schema_visualization(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    try:
        start = time.time()
        result = await asyncio.to_thread(visualize_schema,credentials)
        if result:
            logging.info("Graph schema visualization query successful")
        end = time.time()
        elapsed_time = end - start
        logging.info(f'Schema result from DB: {result}')
        json_obj = {'api_name':'schema_visualization','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success', data=result,message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        message="Unable to get schema visualization from neo4j database"
        error_message = str(e)
        logging.info(message)
        logging.exception(f'Exception:{error_message}')
        return create_api_response("Failed", message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/populate_graph_schema")
async def populate_graph_schema(
    input_text=Form(None),
    model=Form(None),
    is_schema_description_checked=Form(None),
    is_local_storage=Form(None),
    email=Form(None)
):
    """Populate the graph schema from input text."""
    try:
        start = time.time()
        result = populate_graph_schema_from_text(input_text, model, is_schema_description_checked, is_local_storage)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'populate_graph_schema', 'model':model, 'is_schema_description_checked':is_schema_description_checked, 'input_text':input_text, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=result)
    except Exception as e:
        job_status = "Failed"
        message="Unable to get the schema from text"
        error_message = str(e)
        logging.exception(f'Exception in getting the schema from text:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()


# ---------------------------------------------------------------------------
# Post-Processing
# ---------------------------------------------------------------------------

@router.post("/post_processing")
async def post_processing(credentials: Neo4jCredentials = Depends(get_neo4j_credentials), tasks=Form(None)):
    """Run post-processing tasks on the graph database."""
    try:
        graph = create_graph_database_connection(credentials)
        tasks = set(map(str.strip, json.loads(tasks)))
        api_name = 'post_processing'
        count_response = []
        start = time.time()
        if "materialize_text_chunk_similarities" in tasks:
            await asyncio.to_thread(update_graph, graph)
            api_name = 'post_processing/update_similarity_graph'
            logging.info(f'Updated KNN Graph')

        if "enable_hybrid_search_and_fulltext_search_in_bloom" in tasks:
            await asyncio.to_thread(create_vector_fulltext_indexes, credentials)
            api_name = 'post_processing/enable_hybrid_search_and_fulltext_search_in_bloom'
            logging.info(f'Full Text index created')

        if get_value_from_env("ENTITY_EMBEDDING","False","bool") and "materialize_entity_similarities" in tasks:
            await asyncio.to_thread(create_entity_embedding, graph)
            api_name = 'post_processing/create_entity_embedding'
            logging.info(f'Entity Embeddings created')

        if "graph_schema_consolidation" in tasks :
            await asyncio.to_thread(graph_schema_consolidation, graph)
            api_name = 'post_processing/graph_schema_consolidation'
            logging.info(f'Updated nodes and relationship labels')

        if "enable_communities" in tasks:
            api_name = 'create_communities'
            await asyncio.to_thread(create_communities, credentials.uri, credentials.userName, credentials.password, credentials.database, credentials.email)
            logging.info(f'created communities')

        graphDb_data_Access = graphDBdataAccess(graph)
        document_name = ""
        count_response = graphDb_data_Access.update_node_relationship_count(document_name)
        if count_response:
            count_response = [{"filename": filename, **counts} for filename, counts in count_response.items()]
            logging.info(f'Updated source node with community related counts')

        end = time.time()
        elapsed_time = end - start
        for task in tasks:
            api_name = "post_processing/" + task
            json_obj = {
                'api_name': api_name, 'db_url': credentials.uri, 'userName': credentials.userName,
                'database': credentials.database, 'logging_time': formatted_time(datetime.now(timezone.utc)),
                'elapsed_api_time': f'{elapsed_time:.2f}', 'email': credentials.email
            }
            logger.log_struct(json_obj)
        return create_api_response('Success', data=count_response, message='All tasks completed successfully')

    except Exception as e:
        job_status = "Failed"
        error_message = str(e)
        message = f"Unable to complete tasks"
        logging.exception(f'Exception in post_processing tasks: {error_message}')
        return create_api_response(job_status, message=message, error=error_message)

    finally:
        gc.collect()


# ---------------------------------------------------------------------------
# Status, Delete, Retry, Cancel
# ---------------------------------------------------------------------------

@router.get("/update_extract_status/{file_name}")
async def update_extract_status(
    request: Request,
    file_name: str,
    uri: str = None,
    userName: str = None,
    password: str = None,
    database: str = None,
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials)
):
    """Stream updates on extract status for a given file name."""
    async def generate():
        status = ''
        if password is not None and password != "null":
            decoded_password = decode_password(password)
        else:
            decoded_password = None

        url = uri
        if url and " " in url:
            url= url.replace(" ","+")
        
        if not url:
            url = get_value_from_env("NEO4J_URI")
        if not userName:
            userName = get_value_from_env("NEO4J_USERNAME")
        if not decoded_password:
            decoded_password = get_value_from_env("NEO4J_PASSWORD")
        if not database:
            database = get_value_from_env("NEO4J_DATABASE", "neo4j")
            
        credentials = Neo4jCredentials(uri=url, userName=userName, password=decoded_password, database=database)
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        while True:
            try:
                if await request.is_disconnected():
                    logging.info(" SSE Client disconnected")
                    break
                else:
                    if credentials.user_role == "Admin" and not credentials.target_user_email:
                        owner_filter = None
                    else:
                        owner_filter = credentials.target_user_email or credentials.email
                    result = graphDb_data_Access.get_current_status_document_node(file_name, owner_filter)
                    if len(result) > 0:
                        status = json.dumps({'fileName':file_name,
                        'status':result[0]['Status'],
                        'processingTime':result[0]['processingTime'],
                        'nodeCount':result[0]['nodeCount'],
                        'relationshipCount':result[0]['relationshipCount'],
                        'model':result[0]['model'],
                        'total_chunks':result[0]['total_chunks'],
                        'fileSize':result[0]['fileSize'],
                        'processed_chunk':result[0]['processed_chunk'],
                        'fileSource':result[0]['fileSource'],
                        'chunkNodeCount' : result[0]['chunkNodeCount'],
                        'chunkRelCount' : result[0]['chunkRelCount'],
                        'entityNodeCount' : result[0]['entityNodeCount'],
                        'entityEntityRelCount' : result[0]['entityEntityRelCount'],
                        'communityNodeCount' : result[0]['communityNodeCount'],
                        'communityRelCount' : result[0]['communityRelCount'],
                        'token_usage' : result[0]['token_usage']
                        })
                    yield status
            except asyncio.CancelledError:
                logging.info("SSE Connection cancelled")

    return EventSourceResponse(generate(),ping=60)

@router.get('/document_status/{file_name}')
async def get_document_status(file_name, url, userName, password, database, credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """Get the status of a document in the graph database."""
    decoded_password = decode_password(password)

    try:
        if not url:
            uri = get_value_from_env("NEO4J_URI")
        elif " " in url:
            uri= url.replace(" ","+")
        else:
            uri=url
        
        if not userName:
            userName = get_value_from_env("NEO4J_USERNAME")
        if not decoded_password:
            decoded_password = get_value_from_env("NEO4J_PASSWORD")
        if not database:
            database = get_value_from_env("NEO4J_DATABASE", "neo4j")
            
        credentials= Neo4jCredentials(uri=uri, userName=userName, password=decoded_password, database=database)
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        
        if credentials.user_role == "Admin" and not credentials.target_user_email:
            owner_filter = None
        else:
            owner_filter = credentials.target_user_email or credentials.email
            
        result = graphDb_data_Access.get_current_status_document_node(file_name, owner_filter)
        if len(result) > 0:
            status = {'fileName':file_name,
                'status':result[0]['Status'],
                'processingTime':result[0]['processingTime'],
                'nodeCount':result[0]['nodeCount'],
                'relationshipCount':result[0]['relationshipCount'],
                'model':result[0]['model'],
                'total_chunks':result[0]['total_chunks'],
                'fileSize':result[0]['fileSize'],
                'processed_chunk':result[0]['processed_chunk'],
                'fileSource':result[0]['fileSource'],
                'chunkNodeCount' : result[0]['chunkNodeCount'],
                'chunkRelCount' : result[0]['chunkRelCount'],
                'entityNodeCount' : result[0]['entityNodeCount'],
                'entityEntityRelCount' : result[0]['entityEntityRelCount'],
                'communityNodeCount' : result[0]['communityNodeCount'],
                'communityRelCount' : result[0]['communityRelCount']
                }
        else:
            status = {'fileName':file_name, 'status':'Failed'}
        logging.info(f'Result of document status in refresh : {result}')
        return create_api_response('Success',message="",file_name=status)
    except Exception as e:
        message=f"Unable to get the document status"
        error_message = str(e)
        logging.exception(f'{message}:{error_message}')
        return create_api_response('Failed',message=message)

@router.post("/delete_document_and_entities")
async def delete_document_and_entities(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    filenames=Form(),
    source_types=Form(),
    deleteEntities=Form()
):
    """Delete documents and their entities from the graph database."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        
        if credentials.user_role == "Admin" and not credentials.target_user_email:
            owner_filter = None
        else:
            owner_filter = credentials.target_user_email or credentials.email
            
        files_list_size = await asyncio.to_thread(graphDb_data_Access.delete_file_from_graph, filenames, source_types, deleteEntities, MERGED_DIR, credentials.uri, owner_filter)
        message = f"Deleted {files_list_size} documents with entities from database"
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'delete_document_and_entities','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'filenames':filenames,'deleteEntities':deleteEntities,
                            'source_types':source_types, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',message=message)
    except Exception as e:
        job_status = "Failed"
        message=f"Unable to delete document {filenames}"
        error_message = str(e)
        logging.exception(f'{message}:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/cancelled_job")
async def cancelled_job(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    filenames=Form(None),
    source_types=Form(None)
):
    """Cancel a running job for the given filenames and source types."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        result = manually_cancelled_job(graph, filenames, source_types, MERGED_DIR, credentials.uri)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'cancelled_job','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'filenames':filenames,
                            'source_types':source_types, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',message=result)
    except Exception as e:
        job_status = "Failed"
        message="Unable to cancelled the running job"
        error_message = str(e)
        logging.exception(f'Exception in cancelling the running job:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/retry_processing")
async def retry_processing(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    file_name=Form(),
    retry_condition=Form()
):
    """Set status to retry for a given file name and condition."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'retry_processing', 'db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'filename':file_name,'retry_condition':retry_condition,
                            'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        await asyncio.to_thread(set_status_retry, graph,file_name,retry_condition)
        return create_api_response('Success',message=f"Status set to Ready to Reprocess for filename : {file_name}")
    except Exception as e:
        job_status = "Failed"
        message="Unable to set status to Retry"
        error_message = str(e)
        logging.exception(f'{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()
