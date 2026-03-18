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
import bcrypt
import logging

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')
from src.main import create_graph_database_connection
from src.shared.common_fn import formatted_time
from src.shared.google_auth import require_auth, AuthenticatedUser
from src.shared.secret_vault import get_secret, set_secret, list_secret_keys
import os
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import User, Role
from src.llm import translate_text
from pydantic import BaseModel

async def require_admin(
    user: AuthenticatedUser = Depends(require_auth),
    db: Session = Depends(get_db)
):
    # Admin actions must ALWAYS be mapped to a real admin user in the database.
    # We no longer allow skipping admin checks even if general auth is bypassed.
    
    # Query the user from the database
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=403, detail="User not found in system")
    
    # Check if they have a role and if that role is Admin
    if not db_user.role or db_user.role.name.upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    return user

router = APIRouter(tags=["Administration"])


# =============================================================================
# Secret Vault
# =============================================================================

@router.get("/secrets")
async def get_secrets_list(user: AuthenticatedUser = Depends(require_admin)):
    """Get the list of secret keys stored in the vault."""
    try:
        keys = list_secret_keys()
        return create_api_response("Success", data=keys)
    except Exception as e:
        return create_api_response("Failed", error=str(e))

@router.get("/secrets/values")
async def get_secret_value(name: str, user: AuthenticatedUser = Depends(require_admin)):
    """Get the plaintext value of a secret from the vault (admin-only)."""
    try:
        value = get_secret(name)
        if value is None:
            return create_api_response("Failed", message=f"Secret '{name}' not found")
        return create_api_response("Success", data=value)
    except Exception as e:
        return create_api_response("Failed", error=str(e))


class PasswordUpdateRequest(BaseModel):
    password: str

@router.post("/update-password")
async def update_password(request: PasswordUpdateRequest, db: Session = Depends(get_db), current_user = Depends(require_auth)):
    logging.info(f"Update password request for user: {current_user.email}")
    try:
        new_password = request.password
        if not new_password:
            logging.warning("Password update failed: No password provided")
            return create_api_response("Failed", message="Password is required")
        
        db_user = db.query(User).filter(User.email == current_user.email).first()
        if not db_user:
            logging.warning(f"Password update failed: User {current_user.email} not found in DB")
            return create_api_response("Failed", message="User not found")
        
        logging.info(f"Hasing and saving new password for {current_user.email}")
        db_user.hashed_password = hash_password(new_password)
        db.commit()
        logging.info(f"Password update successful for {current_user.email}")
        return create_api_response("Success", message="Password updated successfully")
    except Exception as e:
        logging.exception(f"Password update error: {e}")
        return create_api_response("Failed", error=str(e))


@router.post("/secrets")
async def save_secret(request: Request, user: AuthenticatedUser = Depends(require_admin)):
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
async def get_unconnected_nodes_list(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    user: AuthenticatedUser = Depends(require_admin)
):
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
    unconnected_entities_list=Form(),
    user: AuthenticatedUser = Depends(require_admin)
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
async def get_duplicate_nodes(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    user: AuthenticatedUser = Depends(require_admin)
):
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
    duplicate_nodes_list=Form(),
    user: AuthenticatedUser = Depends(require_admin)
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
    isVectorIndexExist=Form(),
    user: AuthenticatedUser = Depends(require_admin)
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

@router.post("/translate")
async def translate(request: Request):
    """Translate text using Sarvam AI Cloud API with PostgreSQL caching."""
    try:
        payload = await request.json()
        text = payload.get("text", "")
        target_lang = payload.get("target_lang", "hi")
        source_lang = payload.get("source_lang", "en")

        if not text:
            return create_api_response("Failed", error="Text is required")

        translated = await translate_text(text, target_lang, source_lang)
        return create_api_response("Success", data={"translated_text": translated, "source_lang": source_lang, "target_lang": target_lang})
    except Exception as e:
        return create_api_response("Failed", error=str(e))

@router.get("/translate/cache-stats")
async def cache_stats():
    """Get translation cache statistics (hit rates, cached terms count)."""
    from src.translation_cache import get_cache_stats
    from src.database import SessionLocal
    db = SessionLocal()
    try:
        stats = get_cache_stats(db)
        return create_api_response("Success", data=stats)
    finally:
        db.close()

@router.post("/translate/seed")
async def seed_terms(user: AuthenticatedUser = Depends(require_admin)):
    """Seed medical terminology into the translation cache."""
    from src.seed_medical_terms import seed_medical_terms
    try:
        seed_medical_terms()
        return create_api_response("Success", message="Medical terms seeded successfully")
    except Exception as e:
        return create_api_response("Failed", error=str(e))

