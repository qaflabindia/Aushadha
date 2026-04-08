import asyncio
import gc
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form
from langchain_neo4j import Neo4jGraph

from src.QA_integration import QA_RAG, clear_chat_history
from src.api_response import create_api_response
from src.chunkid_entities import get_entities_from_chunkids
from src.entities.user_credential import Neo4jCredentials, get_neo4j_credentials
from src.graphDB_dataAccess import graphDBdataAccess
from src.graph_query import get_chunktext_results, get_graph_results
from src.logger import CustomLogger
from src.main import create_graph_database_connection
from src.neighbours import get_neighbour_nodes
from src.shared.common_fn import formatted_time
from src.database import get_db
from src.services.access_service import verify_patient_access
from sqlalchemy.orm import Session
from typing import Optional

logger = CustomLogger()
router = APIRouter(tags=["Chat & Query"])


@router.post("/chat_bot")
async def chat_bot(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    model=Form(None),
    question=Form(None),
    document_names=Form(None),
    session_id=Form(None),
    mode=Form(None),
    language=Form("en"),
    patient_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Run QA chat bot on the graph database."""
    if patient_id:
        verify_patient_access(credentials.email, credentials.user_role, patient_id, db)
    elif credentials.user_role == "Patient":
        # For patients, we should ideally fetch their patient_id if not provided
        # But for now, let's assume it should be provided or inferred from user context
        # If the user is a patient, their patient record should be linked.
        pass
    logging.info(f"QA_RAG called at {datetime.now()}")
    qa_rag_start_time = time.time()
    try:
        if mode == "graph":
            graph = Neo4jGraph(url=credentials.uri, username=credentials.userName, password=credentials.password, database=credentials.database, sanitize=True, refresh_schema=True)
        else:
            graph = create_graph_database_connection(credentials)

        graphDb_data_Access = graphDBdataAccess(graph)
        write_access = graphDb_data_Access.check_account_access(database=credentials.database)
        # Fix #16: language instruction must NOT be appended to `question` before QA_RAG — doing so
        # stores the raw instruction string as a HumanMessage in Neo4j chat history, corrupting
        # conversation summaries and history-aware follow-ups. The `language` parameter is already
        # passed to QA_RAG which handles output translation; language-specific prompting belongs
        # inside the LLM chain, not in the user question stored in history.
        # Passed patient_id to QA_RAG
        result = await QA_RAG(graph=graph, model=model, question=question, document_names=document_names, session_id=session_id, mode=mode, write_access=write_access, email=credentials.email, uri=credentials.uri, language=language, patient_id=patient_id)

        total_call_time = time.time() - qa_rag_start_time
        logging.info(f"Total Response time is  {total_call_time:.2f} seconds")
        result["info"]["response_time"] = round(total_call_time, 2)

        json_obj = {'api_name':'chat_bot','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'question':question,'document_names':document_names,
                             'session_id':session_id, 'mode':mode, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{total_call_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")

        return create_api_response('Success',data=result)
    except Exception as e:
        job_status = "Failed"
        message="Unable to get chat response"
        error_message = str(e)
        logging.exception(f'Exception in chat bot:{error_message}')
        return create_api_response(job_status, message=message, error=error_message,data=mode)
    finally:
        gc.collect()

@router.post("/chunk_entities")
async def chunk_entities(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    nodedetails=Form(None),
    entities=Form(),
    mode=Form()
):
    """Extract entities from chunk IDs."""
    try:
        start = time.time()
        result = await asyncio.to_thread(get_entities_from_chunkids,credentials, nodedetails, entities, mode)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'chunk_entities','db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'nodedetails':nodedetails,'entities':entities,
                            'mode':mode, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=result,message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        job_status = "Failed"
        message="Unable to extract entities from chunk ids"
        error_message = str(e)
        logging.exception(f'Exception in chat bot:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/get_neighbours")
async def get_neighbours(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    elementId=Form(None)
):
    """Get neighbour nodes for a given element ID."""
    try:
        start = time.time()
        result = await asyncio.to_thread(get_neighbour_nodes, credentials, element_id=elementId)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'get_neighbours', 'userName':credentials.userName, 'database':credentials.database,'db_url':credentials.uri, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=result,message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        job_status = "Failed"
        message="Unable to extract neighbour nodes for given element ID"
        error_message = str(e)
        logging.exception(f'Exception in get neighbours :{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/graph_query")
async def graph_query(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    document_names: str = Form(None),
    language: str = Form("en"),
    model: str = Form(None),
    patient_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Query the graph for results based on document names."""
    if patient_id:
        verify_patient_access(credentials.email, credentials.user_role, patient_id, db)
    try:
        start = time.time()
        result = await get_graph_results(
            credentials,
            document_names=document_names,
            language=language,
            model=model,
            patient_id=patient_id
        )
        end = time.time()
        elapsed_time = end - start
        json_obj = {
            'api_name': 'graph_query',
            'db_url': credentials.uri,
            'userName': credentials.userName,
            'database': credentials.database,
            'document_names': document_names,
            'language': language,
            'model': model,
            'logging_time': formatted_time(datetime.now(timezone.utc)),
            'elapsed_api_time': f'{elapsed_time:.2f}',
            'email': credentials.email
        }
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success', data=result,message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        job_status = "Failed"
        message = "Unable to get graph query response"
        error_message = str(e)
        logging.exception(f'Exception in graph query: {error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()


@router.post("/clear_chat_bot")
async def clear_chat_bot(
    credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
    session_id=Form(None)
):
    """Clear chat history for a given session."""
    try:
        start = time.time()
        graph = create_graph_database_connection(credentials)
        result = await asyncio.to_thread(clear_chat_history,graph=graph,session_id=session_id)
        end = time.time()
        elapsed_time = end - start
        json_obj = {'api_name':'clear_chat_bot', 'db_url':credentials.uri, 'userName':credentials.userName, 'database':credentials.database, 'session_id':session_id, 'logging_time': formatted_time(datetime.now(timezone.utc)), 'elapsed_api_time':f'{elapsed_time:.2f}','email':credentials.email}
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success',data=result)
    except Exception as e:
        job_status = "Failed"
        message="Unable to clear chat History"
        error_message = str(e)
        logging.exception(f'Exception in chat bot:{error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()

@router.post("/fetch_chunktext")
async def fetch_chunktext(
   credentials: Neo4jCredentials = Depends(get_neo4j_credentials),
   document_name: str = Form(),
   page_no: int = Form(1),
   patient_id: Optional[str] = Form(None),
   db: Session = Depends(get_db)
):
    if patient_id:
        verify_patient_access(credentials.email, credentials.user_role, patient_id, db)
    try:
        start = time.time()
        result = await asyncio.to_thread(
            get_chunktext_results,
            credentials,
            document_name=document_name,
            page_no=page_no,
            patient_id=patient_id
        )
        end = time.time()
        elapsed_time = end - start
        json_obj = {
            'api_name': 'fetch_chunktext',
            'db_url': credentials.uri,
            'userName': credentials.userName,
            'database': credentials.database,
            'document_name': document_name,
            'page_no': page_no,
            'logging_time': formatted_time(datetime.now(timezone.utc)),
            'elapsed_api_time': f'{elapsed_time:.2f}',
            'email': credentials.email
        }
        logger.log_struct(json_obj, "INFO")
        return create_api_response('Success', data=result, message=f"Total elapsed API time {elapsed_time:.2f}")
    except Exception as e:
        job_status = "Failed"
        message = "Unable to get chunk text response"
        error_message = str(e)
        logging.exception(f'Exception in fetch_chunktext: {error_message}')
        return create_api_response(job_status, message=message, error=error_message)
    finally:
        gc.collect()
