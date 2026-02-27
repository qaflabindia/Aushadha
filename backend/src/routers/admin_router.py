import asyncio
import gc
import json
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request

from src.api_response import create_api_response
from src.entities.user_credential import Neo4jCredentials, get_neo4j_credentials
from src.graphDB_dataAccess import graphDBdataAccess
from src.logger import CustomLogger
from src.main import create_graph_database_connection
from src.shared.common_fn import formatted_time
from src.shared.google_auth import require_auth, AuthenticatedUser
from src.shared.secret_vault import get_secret, set_secret, list_secret_keys

logger = CustomLogger()
router = APIRouter(tags=["Administration"])


# =============================================================================
# Secret Vault
# =============================================================================

@router.get("/secrets")
async def get_secrets_list(user: AuthenticatedUser = Depends(require_auth)):
    """Get the list of secret keys stored in the vault."""
    try:
        keys = list_secret_keys()
        return create_api_response("Success", data=keys)
    except Exception as e:
        return create_api_response("Failed", error=str(e))

@router.get("/secrets/values")
async def get_secret_value(name: str, user: AuthenticatedUser = Depends(require_auth)):
    """Get the value of a secret from the vault."""
    try:
        value = get_secret(name)
        if value is None:
            return create_api_response("Failed", message=f"Secret '{name}' not found")
        return create_api_response("Success", data={"name": name, "value": value})
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.post("/secrets")
async def save_secret(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Save a secret to the vault."""
    try:
        data = await request.json()
        name = data.get("name")
        value = data.get("value")
        if not name or not value:
            return create_api_response("Failed", message="Both 'name' and 'value' are required")
        set_secret(name, value)
        return create_api_response("Success", message=f"Secret '{name}' saved successfully")
    except Exception as e:
        return create_api_response("Failed", error=str(e))


# =============================================================================
# Graph Node Management
# =============================================================================

@router.post("/get_unconnected_nodes_list")
async def get_unconnected_nodes_list(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """Get the list of unconnected nodes in the graph database."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        nodes_list, total_nodes = graphDb_data_Access.list_unconnected_nodes()
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'get_unconnected_nodes_list','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=nodes_list,message=total_nodes)
    except Exception as e:
        job_status = "Failed"
        message="Unable to get the list of unconnected nodes"
        error_message = str(e)
        logging.exception(f'Exception in getting list of unconnected nodes:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/delete_unconnected_nodes")
async def delete_orphan_nodes(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    unconnected_entities_list=Form()
):
    """Delete unconnected (orphan) nodes from the graph database."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        result = graphDb_data_Access.delete_unconnected_nodes(unconnected_entities_list)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'delete_unconnected_nodes','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,'unconnected_entities_list':unconnected_entities_list, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=result,message="Unconnected entities delete successfully")
    except Exception as e:
        job_status = "Failed"
        message="Unable to delete the unconnected nodes"
        error_message = str(e)
        logging.exception(f'Exception in delete the unconnected nodes:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/get_duplicate_nodes")
async def get_duplicate_nodes(credentials: Neo4jCredentials = Depends(get_neo4j_credentials)):
    """Get the list of duplicate nodes in the graph database."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        nodes_list, total_nodes = graphDb_data_Access.get_duplicate_nodes_list()
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'get_duplicate_nodes','db_url':credentials.uri,'userName':credentials.userName, 'database':credentials.database, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=nodes_list, message=total_nodes)
    except Exception as e:
        job_status = "Failed"
        message="Unable to get the list of duplicate nodes"
        error_message = str(e)
        logging.exception(f'Exception in getting list of duplicate nodes:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/merge_duplicate_nodes")
async def merge_duplicate_nodes(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    duplicate_nodes_list=Form()
):
    """Merge duplicate nodes in the graph database."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        result = graphDb_data_Access.merge_duplicate_nodes(duplicate_nodes_list)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'merge_duplicate_nodes','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,
                            'duplicate_nodes_list':duplicate_nodes_list, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=result,message="Duplicate entities merged successfully")
    except Exception as e:
        job_status = "Failed"
        message="Unable to merge the duplicate nodes"
        error_message = str(e)
        logging.exception(f'Exception in merge the duplicate nodes:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/drop_create_vector_index")
async def drop_create_vector_index(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    isVectorIndexExist=Form()
):
    """Drop and re-create the vector index in the graph database."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        graphDb_data_Access = graphDBdataAccess(graph)
        result = graphDb_data_Access.drop_create_vector_index(isVectorIndexExist)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'drop_create_vector_index', 'db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database,
                            'isVectorIndexExist':isVectorIndexExist, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',message=result)
    except Exception as e:
        job_status = "Failed"
        message="Unable to drop and re-create vector index with correct dimesion as per application configuration"
        error_message = str(e)
        logging.exception(f'Exception into drop and re-create vector index with correct dimesion as per application configuration:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()
