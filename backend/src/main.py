import hashlib
import json
import logging
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.parse
from typing import Optional, List, Dict, Any
import warnings
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.document_loaders import WikipediaLoader, WebBaseLoader
from langchain_neo4j import Neo4jGraph

from src.create_chunks import CreateChunksofDocument
from src.document_sources.gcs_bucket import (
    copy_failed_file, delete_file_from_gcs, get_documents_from_gcs,
    get_gcs_bucket_files_info, merge_file_gcs, upload_file_to_gcs
)
from src.document_sources.local_file import get_documents_from_file_by_path
from src.document_sources.s3_bucket import get_documents_from_s3, get_s3_files_info
from src.document_sources.web_pages import get_documents_from_web_page
from src.document_sources.wikipedia import get_documents_from_wikipedia
from src.document_sources.youtube import get_documents_from_youtube, get_youtube_combined_transcript
from src.entities.source_node import sourceNode
from src.graph_query import get_graphDB_driver
from src.graphDB_dataAccess import graphDBdataAccess
from src.llm import get_graph_from_llm
from src.make_relationships import (
    create_chunk_embeddings, create_chunk_vector_index, create_relation_between_chunks,
    execute_graph_query, merge_relationship_between_chunk_and_entites
)
from src.shared.common_fn import (
    check_url_source, create_gcs_bucket_folder_name_hashed, create_graph_database_connection,
    delete_uploaded_local_file, get_chunk_and_graphDocument,
    handle_backticks_nodes_relationship_id_type, last_url_segment, save_graphDocuments_in_neo4j, track_token_usage
)
from src.shared.common_fn import formatted_time
from src.shared.env_utils import get_value_from_env

from src.shared.constants import (
    DELETE_ENTITIES_AND_START_FROM_BEGINNING, QUERY_TO_DELETE_EXISTING_ENTITIES,
    QUERY_TO_GET_CHUNKS, QUERY_TO_GET_LAST_PROCESSED_CHUNK_POSITION,
    QUERY_TO_GET_LAST_PROCESSED_CHUNK_WITHOUT_ENTITY, QUERY_TO_GET_NODES_AND_RELATIONS_OF_A_DOCUMENT,
    START_FROM_BEGINNING, START_FROM_LAST_PROCESSED_POSITION
)
from src.shared.llm_graph_builder_exception import LLMGraphBuilderException
from src.shared.schema_extraction import schema_extraction_from_text

warnings.filterwarnings("ignore")
load_dotenv()

logging.basicConfig(format='%(asctime)s - %(message)s', level='INFO')
from src.shared.config import GCS_FILE_CACHE, BUCKET_UPLOAD_FILE, BUCKET_FAILED_FILE, PROJECT_ID

# PostgreSQL Integration
from src.database import engine, SessionLocal
from src.services.ingestion_service import IngestionService


def sanitize_uploaded_fileName(filename, max_length=100):
    """
    Sanitize filename to remove problematic characters and limit length.
    If filename is too long or contains non-ASCII, use a hash for uniqueness.

    Args:
        filename (str): The original filename.
        max_length (int): Maximum allowed length for the filename.

    Returns:
        str: Sanitized filename.
    """
    print("Original incoming file Name:", filename)
    filename = os.path.basename(filename) # Prevent path traversal
    safe_name = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', safe_name)
    if '.' in safe_name:
        base, ext = os.path.splitext(safe_name)
    else:
        base, ext = safe_name, ''
    if len(safe_name) == 0 or len(safe_name) > max_length:
        hash_part = hashlib.sha256(filename.encode('utf-8')).hexdigest()[:16]
        base_truncated = base[:max_length - len(ext) - 17] if len(base) > 0 else 'file'
        safe_name = base_truncated + '_' + hash_part + ext
    print("Sanitized filename:", safe_name)
    return safe_name


def create_source_node_graph_url_s3(graph, params, credentials):
    """
    Create source nodes in the graph for files in an S3 bucket.

    Args:
        graph: Neo4j graph connection.
        params: SourceScanExtractParams object.

    Returns:
        tuple: (list of file info dicts, success_count, failed_count)
    """
    lst_file_name = []
    files_info = get_s3_files_info(
        params.source_url,
        aws_access_key_id=params.aws_access_key_id,
        aws_secret_access_key=params.aws_secret_access_key
    )
    if not files_info:
        raise LLMGraphBuilderException('No pdf files found.')
    logging.info('files info : %s', files_info)
    success_count = 0
    failed_count = 0

    for file_info in files_info:
        file_name = file_info['file_key']
        obj_source_node = sourceNode()
        obj_source_node.file_name = str(file_name.split('/')[-1]).strip()
        obj_source_node.file_type = file_name.split('.')[-1].lower() if '.' in file_name else 'pdf'
        obj_source_node.file_size = file_info['file_size_bytes']
        obj_source_node.file_source = params.source_type
        obj_source_node.model = params.model
        obj_source_node.url = str(params.source_url + file_name)
        obj_source_node.awsAccessKeyId = params.aws_access_key_id
        obj_source_node.created_at = datetime.now()
        obj_source_node.chunkNodeCount = 0
        obj_source_node.chunkRelCount = 0
        obj_source_node.entityNodeCount = 0
        obj_source_node.entityEntityRelCount = 0
        obj_source_node.communityNodeCount = 0
        obj_source_node.communityRelCount = 0
        try:
            obj_source_node.patient_id = params.patient_id
            graphDb_data_Access = graphDBdataAccess(graph)
            graphDb_data_Access.create_source_node(obj_source_node)
            success_count += 1
            lst_file_name.append({
                'fileName': obj_source_node.file_name,
                'fileSize': obj_source_node.file_size,
                'url': obj_source_node.url,
                'status': 'Success'
            })
        except Exception as e:
            logging.exception(f"Failed to process S3 file {obj_source_node.file_name}: {e}")
            failed_count += 1
            lst_file_name.append({
                'fileName': obj_source_node.file_name,
                'fileSize': obj_source_node.file_size,
                'url': obj_source_node.url,
                'status': 'Failed'
            })
    return lst_file_name, success_count, failed_count


def create_source_node_graph_url_gcs(graph, params, credentials):
    """
    Create source nodes in the graph for files in a GCS bucket.

    Args:
        graph: Neo4j graph connection.
        params: SourceScanExtractParams object.
        credentials: Google OAuth2 credentials.

    Returns:
        tuple: (list of file info dicts, success_count, failed_count)
    """
    success_count = 0
    failed_count = 0
    lst_file_name = []
    
    lst_file_metadata= get_gcs_bucket_files_info(params.gcs_project_id, params.gcs_bucket_name, params.gcs_bucket_folder, credentials)
    for file_metadata in lst_file_metadata :
      obj_source_node = sourceNode()
      obj_source_node.file_name = str(file_metadata['fileName']).strip()
      obj_source_node.file_size = file_metadata['fileSize']
      obj_source_node.url = file_metadata['url']
      obj_source_node.file_source = params.source_type
      obj_source_node.model = params.model
      obj_source_node.file_type = obj_source_node.file_name.split('.')[-1].lower() if '.' in obj_source_node.file_name else 'pdf'
      obj_source_node.gcsBucket = params.gcs_bucket_name
      obj_source_node.gcsBucketFolder = file_metadata['gcsBucketFolder']
      obj_source_node.gcsProjectId = file_metadata['gcsProjectId']
      obj_source_node.created_at = datetime.now()
      # Explicitly NOT persisting the oauth access_token directly onto the graph node (C1)
      obj_source_node.chunkNodeCount=0
      obj_source_node.chunkRelCount=0
      obj_source_node.entityNodeCount=0
      obj_source_node.entityEntityRelCount=0
      obj_source_node.communityNodeCount=0
      obj_source_node.communityRelCount=0
    
      try:
          obj_source_node.patient_id = params.patient_id
          graphDb_data_Access = graphDBdataAccess(graph)
          graphDb_data_Access.create_source_node(obj_source_node)
          success_count+=1
          lst_file_name.append({'fileName':obj_source_node.file_name,'fileSize':obj_source_node.file_size,'url':obj_source_node.url,'status':'Success', 
                                'gcsBucketName': params.gcs_bucket_name, 'gcsBucketFolder':obj_source_node.gcsBucketFolder, 'gcsProjectId':obj_source_node.gcsProjectId})
      except Exception as e:
        logging.exception(f"Failed to process GCS file {obj_source_node.file_name}: {e}")
        failed_count+=1
        lst_file_name.append({'fileName':obj_source_node.file_name,'fileSize':obj_source_node.file_size,'url':obj_source_node.url,'status':'Failed', 
                              'gcsBucketName': params.gcs_bucket_name, 'gcsBucketFolder':obj_source_node.gcsBucketFolder, 'gcsProjectId':obj_source_node.gcsProjectId})
    return lst_file_name,success_count,failed_count

def create_source_node_graph_web_url(graph, params, credentials):
    """
    Create a source node in the graph for a web page.

    Args:
        graph: Neo4j graph connection.
        params: SourceScanExtractParams object.

    Returns:
        tuple: (list of file info dicts, success_count, failed_count)
    """
    success_count=0
    failed_count=0
    lst_file_name = []
    pages = WebBaseLoader(params.source_url).load()
    if pages==None or len(pages)==0:
      message = f"Unable to read data for given url : {params.source_url}"
      raise LLMGraphBuilderException(message)
    try:
      title = pages[0].metadata['title'].strip()
      if title:
        graphDb_data_Access = graphDBdataAccess(graph)
        existing_url_records = graphDb_data_Access.get_websource_url(title)
        existing_urls = [r['url'] for r in existing_url_records]
        if existing_urls and params.source_url not in existing_urls:
          title = str(title) + "-" + str(last_url_segment(params.source_url)).strip()
      else:
        title = last_url_segment(params.source_url)
      language = pages[0].metadata['language']
    except Exception:
      title = last_url_segment(params.source_url)
      language = "N/A"

    obj_source_node = sourceNode()
    obj_source_node.file_type = 'text'
    obj_source_node.file_source = params.source_type
    obj_source_node.model = params.model
    obj_source_node.url = urllib.parse.unquote(params.source_url)
    obj_source_node.created_at = datetime.now()
    obj_source_node.file_name = str(title).strip()
    obj_source_node.language = language
    obj_source_node.file_size = sys.getsizeof(pages[0].page_content)
    obj_source_node.chunkNodeCount=0
    obj_source_node.chunkRelCount=0
    obj_source_node.entityNodeCount=0
    obj_source_node.entityEntityRelCount=0
    obj_source_node.communityNodeCount=0
    obj_source_node.communityRelCount=0
    obj_source_node.patient_id = params.patient_id
    graphDb_data_Access = graphDBdataAccess(graph)
    graphDb_data_Access.create_source_node(obj_source_node)
    lst_file_name.append({'fileName':obj_source_node.file_name,'fileSize':obj_source_node.file_size,'url':obj_source_node.url,'status':'Success'})
    success_count+=1
    return lst_file_name,success_count,failed_count
  
def create_source_node_graph_url_youtube(graph, params, credentials):
    """
    Create a source node in the graph for a YouTube video.

    Args:
        graph: Neo4j graph connection.
        params: SourceScanExtractParams object.

    Returns:
        tuple: (list of file info dicts, success_count, failed_count)
    """
    youtube_url, language = check_url_source(source_type=params.source_type, yt_url=params.source_url)
    success_count=0
    failed_count=0
    lst_file_name = []
    obj_source_node = sourceNode()
    obj_source_node.file_type = 'text'
    obj_source_node.file_source = params.source_type
    obj_source_node.model = params.model
    obj_source_node.url = youtube_url
    obj_source_node.created_at = datetime.now()
    obj_source_node.chunkNodeCount=0
    obj_source_node.chunkRelCount=0
    obj_source_node.entityNodeCount=0
    obj_source_node.entityEntityRelCount=0
    obj_source_node.communityNodeCount=0
    obj_source_node.communityRelCount=0
    match = re.search(r'(?:v=)([0-9A-Za-z_-]{11})\s*',obj_source_node.url)
    logging.info(f"match value: {match}")
    if not match:
      raise LLMGraphBuilderException(f"Cannot extract YouTube video ID from URL: {obj_source_node.url}")
    video_id = match.group(1)
    obj_source_node.file_name = video_id
    transcript= get_youtube_combined_transcript(video_id)
    # logging.info(f"Youtube transcript : {transcript}")
    if transcript==None or len(transcript)==0:
      message = f"Youtube transcript is not available for : {obj_source_node.file_name}"
      raise LLMGraphBuilderException(message)
    else:  
      obj_source_node.file_size = sys.getsizeof(transcript)
    
    obj_source_node.patient_id = params.patient_id
    graphDb_data_Access = graphDBdataAccess(graph)
    graphDb_data_Access.create_source_node(obj_source_node)
    lst_file_name.append({'fileName':obj_source_node.file_name,'fileSize':obj_source_node.file_size,'url':obj_source_node.url,'status':'Success'})
    success_count+=1
    return lst_file_name,success_count,failed_count

def create_source_node_graph_url_wikipedia(graph, params, credentials):
    """
    Create a source node in the graph for a Wikipedia page.

    Args:
        graph: Neo4j graph connection.
        params: SourceScanExtractParams object.

    Returns:
        tuple: (list of file info dicts, success_count, failed_count)
    """
    success_count=0
    failed_count=0
    lst_file_name=[]
    wiki_query_id, language = check_url_source(source_type=params.source_type, wiki_query=params.wiki_query)
    logging.info(f"Creating source node for {wiki_query_id.strip()}, {language}")
    pages = WikipediaLoader(query=wiki_query_id.strip(), lang=language, load_max_docs=1, load_all_available_meta=True).load()
    if pages==None or len(pages)==0:
      failed_count+=1
      message = f"Unable to read data for given Wikipedia url : {params.wiki_query}"
      raise LLMGraphBuilderException(message)
    else:
      obj_source_node = sourceNode()
      obj_source_node.file_name = wiki_query_id.strip()
      obj_source_node.file_type = 'text'
      obj_source_node.file_source = params.source_type
      obj_source_node.file_size = sys.getsizeof(pages[0].page_content)
      obj_source_node.model = params.model
      obj_source_node.url = urllib.parse.unquote(pages[0].metadata['source'])
      obj_source_node.created_at = datetime.now()
      obj_source_node.language = language
      obj_source_node.chunkNodeCount=0
      obj_source_node.chunkRelCount=0
      obj_source_node.entityNodeCount=0
      obj_source_node.entityEntityRelCount=0
      obj_source_node.communityNodeCount=0
      obj_source_node.communityRelCount=0
      obj_source_node.patient_id = params.patient_id
      graphDb_data_Access = graphDBdataAccess(graph)
      graphDb_data_Access.create_source_node(obj_source_node)
      success_count+=1
      lst_file_name.append({'fileName':obj_source_node.file_name,'fileSize':obj_source_node.file_size,'url':obj_source_node.url, 'language':obj_source_node.language, 'status':'Success'})
    return lst_file_name,success_count,failed_count
    
async def extract_graph_from_file_local_file(credentials, params, merged_file_path):
    logging.info(f'Process file name :{params.file_name} from local file system')
    if GCS_FILE_CACHE:
        folder_name = create_gcs_bucket_folder_name_hashed(credentials.uri, params.file_name)
        file_name, pages = get_documents_from_gcs(PROJECT_ID, BUCKET_UPLOAD_FILE, folder_name, params.file_name)
        params.file_name = file_name  # Fix #11: GCS path must also update params.file_name
    else:
        file_name, pages, file_extension = get_documents_from_file_by_path(merged_file_path, params.file_name)
        params.file_name = file_name
    
    return await IngestionService.process_document(credentials, params, pages, merged_file_path, is_uploaded_from_local=True)
  
async def extract_graph_from_file_s3(credentials, params):
    if params.aws_access_key_id is None or params.aws_secret_access_key is None:
        raise LLMGraphBuilderException('Please provide AWS access and secret keys')
    
    logging.info("Processing S3 Source")
    file_name, pages = get_documents_from_s3(params.source_url, params.aws_access_key_id, params.aws_secret_access_key)
    return await IngestionService.process_document(credentials, params, pages)
  
async def extract_graph_from_web_page(credentials, params):
    pages = get_documents_from_web_page(params.source_url)
    return await IngestionService.process_document(credentials, params, pages)
  
async def extract_graph_from_file_youtube(credentials, params):
    file_name, pages = get_documents_from_youtube(params.source_url)
    return await IngestionService.process_document(credentials, params, pages)
    
async def extract_graph_from_file_Wikipedia(credentials, params):
    file_name, pages = get_documents_from_wikipedia(params.wiki_query, params.language)
    return await IngestionService.process_document(credentials, params, pages)

async def extract_graph_from_file_gcs(credentials, params):
    from src.services.ingestion_service import IngestionService
    file_name, pages = get_documents_from_gcs(params.gcs_project_id, params.gcs_bucket_name, params.gcs_bucket_folder, params.gcs_blob_filename, params.access_token)
    return await IngestionService.process_document(credentials, params, pages)
  
# processing_source and processing_chunks have been moved to IngestionService and ExtractionService

def get_chunkId_chunkDoc_list(graph, file_name, pages, token_chunk_size, chunk_overlap, retry_condition, email, patient_id=None):
  """
  Get chunk IDs and corresponding document chunks for a file.

  Args:
      graph: Neo4j graph connection.
      file_name (str): Name of the file.
      pages (list): List of document pages.
      token_chunk_size (int): Token size for chunking.
      chunk_overlap (int): Overlap size for chunks.
      retry_condition (str): Condition for retrying chunk creation.
      email (str): User email for tracking.

  Returns:
      tuple: (total_chunks, chunkId_chunkDoc_list)
  """
  if retry_condition in ["", None] or retry_condition not in [DELETE_ENTITIES_AND_START_FROM_BEGINNING, START_FROM_LAST_PROCESSED_POSITION]:
    logging.info("Break down file into chunks")
    bad_chars = ['"', "\n", "'"]
    for i in range(0,len(pages)):
      text = pages[i].page_content
      for j in bad_chars:
        if j == '\n':
          text = text.replace(j, ' ')
        else:
          text = text.replace(j, '')
      pages[i]=Document(page_content=str(text), metadata=pages[i].metadata)
    create_chunks_obj = CreateChunksofDocument(pages, graph)
    chunks = create_chunks_obj.split_file_into_chunks(token_chunk_size, chunk_overlap, email)
    chunkId_chunkDoc_list = create_relation_between_chunks(graph, file_name, chunks, patient_id=patient_id)
    return len(chunks), chunkId_chunkDoc_list
  
  else:  
    chunkId_chunkDoc_list=[]
    chunks =  execute_graph_query(graph,QUERY_TO_GET_CHUNKS, params={"filename":file_name, "patient_id": patient_id})
    
    if not chunks or chunks[0]['text'] is None or chunks[0]['text']=="" :
      raise LLMGraphBuilderException(f"Chunks are not created for {file_name}. Please re-upload file or reprocess the file with option Start From Beginning.")    
    else:
      for chunk in chunks:
        chunk_doc = Document(page_content=chunk['text'], metadata={'id':chunk['id'], 'position':chunk['position']})
        chunkId_chunkDoc_list.append({'chunk_id': chunk['id'], 'chunk_doc': chunk_doc})
      
      if retry_condition ==  START_FROM_LAST_PROCESSED_POSITION:
        logging.info(f"Retry : start_from_last_processed_position")
        starting_chunk = execute_graph_query(graph,QUERY_TO_GET_LAST_PROCESSED_CHUNK_POSITION, params={"filename":file_name})
        
        if starting_chunk and starting_chunk[0]["position"] < len(chunkId_chunkDoc_list):
          return len(chunks), chunkId_chunkDoc_list[starting_chunk[0]["position"] - 1:]
        
        elif starting_chunk and starting_chunk[0]["position"] == len(chunkId_chunkDoc_list):
          starting_chunk =  execute_graph_query(graph,QUERY_TO_GET_LAST_PROCESSED_CHUNK_WITHOUT_ENTITY, params={"filename":file_name})
          return len(chunks), chunkId_chunkDoc_list[starting_chunk[0]["position"] - 1:]
        
        else:
          raise LLMGraphBuilderException(f"All chunks of file {file_name} are already processed. If you want to re-process, Please start from begnning")    
      
      else:
        logging.info(f"Retry : start_from_beginning with chunks {len(chunkId_chunkDoc_list)}")    
        return len(chunks), chunkId_chunkDoc_list
  
def get_source_list_from_graph(credentials, patient_id: Optional[str] = None):
  
  logging.info("Get existing files list from graph")
  graph = Neo4jGraph(url=credentials.uri, database=credentials.database, username=credentials.userName, password=credentials.password)
  graph_DB_dataAccess = graphDBdataAccess(graph)

  try:
      return graph_DB_dataAccess.get_source_list(patient_id=patient_id)
  finally:
      if not graph._driver._closed:
          logging.info(f"closing connection for sources_list api")
          graph._driver.close()

def update_graph(graph):
  """
  Update the graph node with SIMILAR relationship where embedding scrore match
  """
  graph_DB_dataAccess = graphDBdataAccess(graph)
  graph_DB_dataAccess.update_KNN_graph()

  
def connection_check_and_get_vector_dimensions(graph,database):
  """
  Args:
    uri: URI of the graph to extract
    userName: Username to use for graph creation ( if None will use username from config file )
    password: Password to use for graph creation ( if None will use password from config file )
    db_name: db_name is database name to connect to graph db
  Returns:
   Returns a status of connection from NEO4j is success or failure
 """
  graph_DB_dataAccess = graphDBdataAccess(graph)
  return graph_DB_dataAccess.connection_check_and_get_vector_dimensions(database)


def merge_chunks_local(file_name, total_chunks, chunk_dir, merged_dir):
  """
  Merge file chunks into a single file locally.

  Args:
      file_name (str): Name of the original file.
      total_chunks (int): Total number of chunks.
      chunk_dir (str): Directory where chunks are stored.
      merged_dir (str): Directory where the merged file will be saved.

  Returns:
      int: Size of the merged file.
  """
  if not os.path.exists(merged_dir):
    os.mkdir(merged_dir)
  logging.info(f'Merged File Path: {merged_dir}')
  merged_file_path = os.path.join(merged_dir, file_name)
  with open(merged_file_path, "wb") as write_stream:
    for i in range(1, total_chunks + 1):
      chunk_file_path = os.path.join(chunk_dir, f"{file_name}_part_{i}")
      logging.info(f'Chunk File Path While Merging Parts:{chunk_file_path}')
      with open(chunk_file_path, "rb") as chunk_file:
        shutil.copyfileobj(chunk_file, write_stream)
      # Note: individual chunk deletion removed per data retention policy.
  logging.info("Chunks merged successfully and return file size")
  file_size = os.path.getsize(merged_file_path)
  return file_size

def upload_file(graph, model, chunk, chunk_number: int, total_chunks: int, file_name, uri, chunk_dir, merged_dir, patient_id: Optional[str] = None):
    """
    Upload a file or its chunk to the specified destination (GCS or local).

    Args:
        graph: Neo4j graph connection.
        model: Model name used for processing.
        chunk: File chunk to be uploaded.
        chunk_number (int): Chunk number.
        total_chunks (int): Total number of chunks.
        file_name (str): Original file name.
        uri: Database URI.
        chunk_dir (str): Directory for storing chunks.
        merged_dir (str): Directory for storing merged files.

    Returns:
        str: Status message indicating the result of the upload operation.
    """
    # Use sanitized filename for chunk operations
    safe_file_name = sanitize_uploaded_fileName(file_name)
    if GCS_FILE_CACHE:
      folder_name = create_gcs_bucket_folder_name_hashed(uri, safe_file_name)
      upload_file_to_gcs(chunk, chunk_number, safe_file_name, BUCKET_UPLOAD_FILE, folder_name)
    else:
      if not os.path.exists(chunk_dir):
        os.mkdir(chunk_dir)
      chunk_file_path = os.path.join(chunk_dir, f"{safe_file_name}_part_{chunk_number}")
      logging.info(f'Chunk File Path: {chunk_file_path}')
      with open(chunk_file_path, "wb") as chunk_file:
        chunk_file.write(chunk.file.read())

    if int(chunk_number) == int(total_chunks):
        # If this is the last chunk, merge all chunks into a single file
        if GCS_FILE_CACHE:
            file_size = merge_file_gcs(BUCKET_UPLOAD_FILE, safe_file_name, folder_name, int(total_chunks))
        else:
            file_size = merge_chunks_local(safe_file_name, int(total_chunks), chunk_dir, merged_dir)
        logging.info("File merged successfully")
        file_extension = safe_file_name.split('.')[-1] if '.' in safe_file_name else ''  # Fix #14: dotless filenames
        obj_source_node = sourceNode()
        obj_source_node.file_name = str(safe_file_name).strip()
        obj_source_node.file_type = file_extension
        obj_source_node.file_size = file_size
        obj_source_node.file_source = 'local file'
        obj_source_node.model = model
        obj_source_node.created_at = datetime.now()
        obj_source_node.chunkNodeCount = 0
        obj_source_node.chunkRelCount = 0
        obj_source_node.entityNodeCount = 0
        obj_source_node.entityEntityRelCount = 0
        obj_source_node.communityNodeCount = 0
        obj_source_node.communityRelCount = 0
        obj_source_node.patient_id = patient_id
        graphDb_data_Access = graphDBdataAccess(graph)
        graphDb_data_Access.create_source_node(obj_source_node)
        return {'file_size': file_size, 'file_name': safe_file_name, 'file_extension': file_extension, 'message': f"Chunk {chunk_number}/{total_chunks} saved"}
    return f"Chunk {chunk_number}/{total_chunks} saved"

def get_labels_and_relationtypes(credentials, patient_id: Optional[str] = None):
  """
  Get distinct labels and relationship types from the graph, optionally filtered by patient.
  """
  graph = Neo4jGraph(url=credentials.uri, database=credentials.database, username=credentials.userName, password=credentials.password)
  graph_db_access = graphDBdataAccess(graph)
  
  try:
      node_labels, relationship_types = graph_db_access.get_nodelabels_relationships(patient_id)
      
      # Now we still need to calculate the triplets if that's what's expected...
      # Wait, the previous implementation returned triplets.
      # If patient_id is provided, I should calculate triplets for that patient.
      
      excluded_labels = {'Document', 'Chunk', '_Bloom_Perspective_', '__Community__', '__Entity__', 'Session', 'Message'}
      excluded_relationships = {
           'NEXT_CHUNK', '_Bloom_Perspective_', 'FIRST_CHUNK',
           'SIMILAR', 'IN_COMMUNITY', 'PARENT_COMMUNITY', 'NEXT', 'LAST_MESSAGE'
       }
      
      triples = set()
      
      if patient_id:
          query = """
          MATCH (d:Document {patient_id: $patient_id})<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(n)-[r]->(m)
          RETURN DISTINCT labels(n) AS fromLabels, type(r) AS relType, labels(m) AS toLabels
          """
          params = {"patient_id": patient_id}
      else:
          query = """
          MATCH (d:Document)<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(n)-[r]->(m)
          WHERE d.patient_id IS NULL
          RETURN DISTINCT labels(n) AS fromLabels, type(r) AS relType, labels(m) AS toLabels
          """
          params = {}
          
      result = graph_db_access.execute_query(query, params)
      for record in result:
          from_labels = record["fromLabels"]
          to_labels = record["toLabels"]
          rel_type = record["relType"]
          from_label = next((lbl for lbl in from_labels if lbl not in excluded_labels), None)
          to_label = next((lbl for lbl in to_labels if lbl not in excluded_labels), None)
          if not from_label or not to_label:
              continue
          if rel_type == 'PART_OF':
              if from_label == 'Chunk' and to_label == 'Document':
                  continue 
          elif rel_type == 'HAS_ENTITY':
              if from_label == 'Chunk':
                  continue 
          elif (
              from_label in excluded_labels or
              to_label in excluded_labels or
              rel_type in excluded_relationships
          ):
              continue
          triples.add(f"{from_label}-{rel_type}->{to_label}")
      return {"triplets": list(triples)}
  finally:
      if not graph._driver._closed:
          graph._driver.close()

def manually_cancelled_job(graph, filenames, source_types, merged_dir, uri, patient_id: Optional[str] = None):
  
  filename_list= list(map(str.strip, json.loads(filenames)))
  source_types_list= list(map(str.strip, json.loads(source_types)))
  
  for (file_name,source_type) in zip(filename_list, source_types_list):
      obj_source_node = sourceNode()
      obj_source_node.file_name = str(file_name).strip()
      obj_source_node.is_cancelled = True
      obj_source_node.status = 'Cancelled'
      obj_source_node.updated_at = datetime.now()
      obj_source_node.patient_id = patient_id
      graphDb_data_Access = graphDBdataAccess(graph)
      graphDb_data_Access.update_source_node(obj_source_node)
      #Update the nodeCount and relCount properties in Document node
      graphDb_data_Access.update_node_relationship_count(file_name, patient_id=patient_id)
      obj_source_node = None
  return "Cancelled the processing job successfully"

def populate_graph_schema_from_text(text, model, is_schema_description_checked, is_local_storage):
  """_summary_

  Args:
      graph (Neo4Graph): Neo4jGraph connection object
      input_text (str): rendom text from PDF or user input.
      model (str): AI model to use extraction from text

  Returns:
      data (list): list of lebels and relationTypes
  """
  result = schema_extraction_from_text(text, model, is_schema_description_checked, is_local_storage)
  return result

def set_status_retry(graph, file_name, retry_condition, patient_id: Optional[str] = None):
    """
    Set the status of a file processing job to 'Ready to Reprocess' in the graph.

    Args:
        graph: Neo4j graph connection.
        file_name (str): Name of the file.
        retry_condition (str): Condition for retrying the job.

    Returns:
        None
    """
    graphDb_data_Access = graphDBdataAccess(graph)
    obj_source_node = sourceNode()
    status = "Ready to Reprocess"
    obj_source_node.file_name = file_name.strip() if isinstance(file_name, str) else file_name
    obj_source_node.status = status
    obj_source_node.retry_condition = retry_condition
    obj_source_node.is_cancelled = False
    if retry_condition == DELETE_ENTITIES_AND_START_FROM_BEGINNING or retry_condition == START_FROM_BEGINNING:
        obj_source_node.processed_chunk=0
        obj_source_node.node_count=0
        obj_source_node.relationship_count=0
        obj_source_node.chunkNodeCount=0
        obj_source_node.chunkRelCount=0
        obj_source_node.communityNodeCount=0
        obj_source_node.communityRelCount=0
        obj_source_node.entityEntityRelCount=0
        obj_source_node.entityNodeCount=0
        obj_source_node.processingTime=0
        obj_source_node.total_chunks=0
    if retry_condition == DELETE_ENTITIES_AND_START_FROM_BEGINNING:
        execute_graph_query(graph,QUERY_TO_DELETE_EXISTING_ENTITIES, params={"filename":file_name, "patient_id": patient_id})
        
    obj_source_node.patient_id = patient_id
    graphDb_data_Access.update_source_node(obj_source_node)

def failed_file_process(uri,file_name, merged_file_path):
  """
  Handle the processing of a failed file by moving it to a failed directory.

  Args:
      uri (str): The URI of the Neo4j database.
      file_name (str): The name of the file that failed to process.
      merged_file_path (str): The path of the merged file.

  Returns:
      None
  """
  if GCS_FILE_CACHE:
      folder_name = create_gcs_bucket_folder_name_hashed(uri,file_name)
      copy_failed_file(BUCKET_UPLOAD_FILE, BUCKET_FAILED_FILE, folder_name, file_name)
      time.sleep(5)
      delete_file_from_gcs(BUCKET_UPLOAD_FILE,folder_name,file_name)
  else:
      logging.info(f'Note: File retention active. No local file deleted for: {file_name}')
      # delete_uploaded_local_file(merged_file_path,file_name)