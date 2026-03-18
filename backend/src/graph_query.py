import logging
from typing import Optional
from neo4j import time 
from neo4j import GraphDatabase
from src.shared.env_utils import get_value_from_env
import os
import json

from src.shared.constants import GRAPH_CHUNK_LIMIT,GRAPH_QUERY,CHUNK_TEXT_QUERY,COUNT_CHUNKS_QUERY,SCHEMA_VISUALIZATION_QUERY
from src.shared.localization import translate_graph_labels
import re

def is_junk_text(text: str) -> bool:
    """Check if the text is conversational junk or filler."""
    if not text:
        return True
    
    # Check length
    if len(text) > 100:
        return True
        
    junk_patterns = [
        r"(?i)okay,?\s*let\'s\s*tackle",
        r"(?i)tackle\s*this",
        r"(?i)the\s*user\s*wrote",
        r"(?i)here\s*is\s*the\s*translation",
        r"(?i)it\s*means",
        r"(?i)intended\s*translation",
        r"(?i)in\s*tamil",
        r"(?i)in\s*hindi",
        r"அடுத்த பகுதி",
        r"உருப்படி உள்ளது",
        r"குறிப்பிடப்பட்டுள்ளது",
    ]
    for pattern in junk_patterns:
        if re.search(pattern, text):
            return True
            
    # Check for sentence-like structures in what should be a label/type
    words = text.split()
    if len(words) > 8:
        return True
        
    return False

def get_graphDB_driver(credentials):
    """
    Creates and returns a Neo4j database driver instance configured with the provided credentials.

    Returns:
    Neo4j.Driver: A driver object for interacting with the Neo4j database.

    """
    try:
        logging.info(f"Attempting to connect to the Neo4j database at {credentials.uri}")
        # Prefer credentials values, fallback to env if missing
        username = credentials.userName if credentials.userName is not None else get_value_from_env('NEO4J_USERNAME')
        password = credentials.password if credentials.password is not None else get_value_from_env('NEO4J_PASSWORD')
        database = credentials.database if hasattr(credentials, 'database') and credentials.database is not None else get_value_from_env('NEO4J_DATABASE')

        enable_user_agent = get_value_from_env("ENABLE_USER_AGENT", "False", "bool")
        if enable_user_agent:
            driver = GraphDatabase.driver(
                credentials.uri,
                auth=(username, password),
                database=database,
                user_agent=get_value_from_env("USER_AGENT", "LLM-Graph-Builder")
            )
        else:
            driver = GraphDatabase.driver(
                credentials.uri,
                auth=(username, password),
                database=database
            )
        logging.info("Connection successful")
        return driver
    except Exception as e:
        error_message = f"graph_query module: Failed to connect to the database at {credentials.uri}."
        logging.error(error_message, exc_info=True)


def execute_query(driver, query,document_names,doc_limit=None, patient_id=None):
    """
    Executes a specified query using the Neo4j driver, with parameters based on the presence of a document name.

    Returns:
    tuple: Contains records, summary of the execution, and keys of the records.
    """
    try:
        if document_names:
            logging.info(f"Executing query for documents: {document_names}")
            records, summary, keys = driver.execute_query(query, document_names=document_names, patient_id=patient_id)
        else:
            logging.info(f"Executing query with a document limit of {doc_limit}")
            records, summary, keys = driver.execute_query(query, doc_limit=doc_limit, patient_id=patient_id)
        return records, summary, keys
    except Exception as e:
        error_message = f"graph_query module: Failed to execute the query. Error: {str(e)}"
        logging.error(error_message, exc_info=True)


def process_node(node):
    """
    Processes a node from a Neo4j database, extracting its ID, labels, and properties,
    while omitting certain properties like 'embedding' and 'text'.
    Returns None if the node's 'id' is considered junk.
    """
    try:
        # Sanity check: Filter out 'junk' nodes based on ID
        node_id = node.get("id")
        if node_id is not None:
            # Check if ID is junk
            if is_junk_text(str(node_id)) or not str(node_id).strip() or re.match(r'^[^a-zA-Z0-9]+$', str(node_id)):
                return None
        
        labels = set(node.labels)
        labels.discard("__Entity__")
        if not labels:
            labels.add('*')
        
        node_element = {
            "element_id": node.element_id,
            "labels": list(labels),
            "properties": {}
        }

        for key in node:
            if key in ["embedding", "text", "summary"]:
                continue
            value = node.get(key)
            if isinstance(value, time.DateTime):
                node_element["properties"][key] = value.isoformat()
            elif isinstance(value, str) and len(value) > 100:
                # Truncate long strings for cleaner graph visualization
                node_element["properties"][key] = value[:97] + "..."
            else:
                node_element["properties"][key] = value

        return node_element
    except Exception as e:
        logging.error(f"graph_query module: An unexpected error occurred while processing the node: {e}")
        return None

def extract_node_elements(records):
    """
    Extracts and processes unique nodes from a list of records, avoiding duplication by tracking seen element IDs.

    Returns:
    list of dict: A list containing processed node dictionaries.
    """
    node_elements = []
    seen_element_ids = set()  

    try:
        for record in records:
            nodes = record.get("nodes", [])
            if not nodes:
                continue

            for node in nodes:
                if node.element_id in seen_element_ids:
                    continue
                
                node_element = process_node(node) 
                if node_element: # Skip if process_node returned None (junk node)
                    seen_element_ids.add(node.element_id)
                    node_elements.append(node_element)

        return node_elements
    except Exception as e:
        logging.error(f"graph_query module: An error occurred while extracting node elements from records: {e}")
        return []

def extract_relationships(records):
    """
    Extracts and processes relationships from a list of records, ensuring that each relationship is processed
    only once by tracking seen element IDs.

    Returns:
    list of dict: A list containing dictionaries of processed relationships.
    """
    all_relationships = []
    seen_element_ids = set()

    try:
        for record in records:
            relationships = []
            relations = record.get("rels", [])
            if not relations:
                continue

            for relation in relations:
                if relation.element_id in seen_element_ids:
                    continue
                seen_element_ids.add(relation.element_id)

                try:
                    # Filter out junk relationship types
                    if is_junk_text(relation.type):
                        continue

                    nodes = relation.nodes
                    if len(nodes) < 2:
                        continue

                    start_node = process_node(nodes[0])
                    end_node = process_node(nodes[1])
                    if start_node and end_node: # Only add if both nodes are valid
                        # Extract relationship properties (omitting embedding/text as we do for nodes)
                        rel_properties = {}
                        for key in relation:
                            if key in ["embedding", "text", "summary"]:
                                continue
                            value = relation.get(key)
                            if isinstance(value, str) and len(value) > 100:
                                rel_properties[key] = value[:97] + "..."
                            else:
                                rel_properties[key] = value

                        relationship = {
                            "element_id": relation.element_id,
                            "type": relation.type,
                            "start_node_element_id": start_node["element_id"],
                            "end_node_element_id": end_node["element_id"],
                            "properties": rel_properties
                        }
                        relationships.append(relationship)

                except Exception as inner_e:
                    logging.error(f"graph_query module: Failed to process relationship with ID {relation.element_id}. Error: {inner_e}", exc_info=True)
            all_relationships.extend(relationships)
        return all_relationships
    except Exception as e:
        logging.error("graph_query module: An error occurred while extracting relationships from records", exc_info=True)


def get_completed_documents(driver, patient_id: Optional[str] = None):
    """
    Retrieves the names of all documents with the status 'Completed' from the database, filtered by patient.
    """
    if patient_id:
        docs_query = "MATCH(node:Document {status:'Completed', patient_id: $patient_id}) RETURN node"
        params = {"patient_id": patient_id}
    else:
        docs_query = "MATCH(node:Document {status:'Completed'}) WHERE node.patient_id IS NULL RETURN node"
        params = {}
    
    try:
        logging.info("Executing query to retrieve completed documents.")
        records, summary, keys = driver.execute_query(docs_query, **params)
        logging.info(f"Query executed successfully, retrieved {len(records)} records.")
        documents = [record["node"]["fileName"] for record in records]
        logging.info("Document names extracted successfully.")
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        documents = []
    
    return documents


async def get_graph_results(credentials, document_names, language="en", model=None, patient_id: Optional[str] = None):
    """
    Retrieves graph data by executing a specified Cypher query using credentials and parameters provided.
    Processes the results to extract nodes and relationships and packages them in a structured output.
    When language is not 'en', node labels and relationship types are translated using LLM.

    Args:
    credentials (Neo4jCredentials): The credentials object containing URI, username, password, and database information.
    document_names (str): A JSON string representing a list of document names to query for, if any.
    language (str): ISO 639-1 language code (e.g., 'hi', 'ta', 'te'). Default 'en'.
    model (str): The name of the LLM to use for translation.
    Returns:
    dict: Contains the session ID, user-defined messages with nodes and relationships, and the user module identifier.
    """
    import asyncio
    try:
        logging.info(f"Starting graph query process")
        driver = get_graphDB_driver(credentials)  
        document_names= list(map(str, json.loads(document_names)))
        query = GRAPH_QUERY.format(graph_chunk_limit=GRAPH_CHUNK_LIMIT)
        records, summary , keys = await asyncio.to_thread(execute_query, driver, query.strip(), document_names, patient_id=patient_id)
        document_nodes = extract_node_elements(records)
        document_relationships = extract_relationships(records)

        # Translate labels and types if language is not English
        if language and language != "en":
            document_nodes, document_relationships = await translate_graph_labels(
                document_nodes, document_relationships, language, model
            )

        logging.info(f"no of nodes : {len(document_nodes)}")
        logging.info(f"no of relations : {len(document_relationships)}")
        result = {
            "nodes": document_nodes,
            "relationships": document_relationships
        }

        logging.info(f"Query process completed successfully")
        return result
    except Exception as e:
        logging.error(f"graph_query module: An error occurred in get_graph_results. Error: {str(e)}")
        raise Exception(f"graph_query module: An error occurred in get_graph_results. Please check the logs for more details.") from e
        logging.info("Closing connection for graph_query api")
        driver.close()



def get_chunktext_results(credentials, document_name, page_no, patient_id: Optional[str] = None):
   """Retrieves chunk text, position, and page number from graph data with pagination."""
   driver = None
   try:
       logging.info("Starting chunk text query process")
       offset = 10
       skip = (page_no - 1) * offset
       limit = offset
       driver = get_graphDB_driver(credentials)  
       with driver.session(database=credentials.database) as session:
           total_chunks_result = session.run(COUNT_CHUNKS_QUERY, file_name=document_name, patient_id=patient_id)
           total_chunks = total_chunks_result.single()["total_chunks"]
           total_pages = (total_chunks + offset - 1) // offset  # Calculate total pages
           records = session.run(CHUNK_TEXT_QUERY, file_name=document_name, skip=skip, limit=limit, patient_id=patient_id)
           pageitems = [
               {
                   "text": record["chunk_text"],
                   "position": record["chunk_position"],
                   "pagenumber": record["page_number"]
               }
               for record in records
           ]
           logging.info(f"Query process completed with {len(pageitems)} chunks retrieved")
           return {
               "pageitems": pageitems,
               "total_pages": total_pages
           }
   except Exception as e:
       logging.error(f"An error occurred in get_chunktext_results. Error: {str(e)}")
       raise Exception("An error occurred in get_chunktext_results. Please check the logs for more details.") from e
   finally:
       if driver:
           driver.close()


def visualize_schema(credentials, patient_id: Optional[str] = None):
   """Retrieves graph schema"""
   driver = None
   try:
      logging.info("Starting visualizing graph schema")
      driver = get_graphDB_driver(credentials)  
      
      if patient_id:
         # Custom query for patient-specific schema
         query = """
         MATCH (d:Document {patient_id: $patient_id})<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(n)-[r]->(m)
         WITH DISTINCT labels(n) AS fromLabels, type(r) AS relType, labels(m) AS toLabels
         RETURN fromLabels, relType, toLabels
         """
         params = {"patient_id": patient_id}
         records, summary, keys = driver.execute_query(query, **params)
         
         # Reconstruct nodes and relationships in the format expected by the frontend
         nodes_map = {}
         rels_list = []
         
         for i, record in enumerate(records):
            from_label = record["fromLabels"][0] if record["fromLabels"] else "Unknown"
            to_label = record["toLabels"][0] if record["toLabels"] else "Unknown"
            rel_type = record["relType"]
            
            if from_label not in nodes_map:
               nodes_map[from_label] = {"element_id": f"node_{from_label}", "labels": [from_label], "properties": {}}
            if to_label not in nodes_map:
               nodes_map[to_label] = {"element_id": f"node_{to_label}", "labels": [to_label], "properties": {}}
            
            rels_list.append({
               "type": rel_type,
               "properties": {},
               "element_id": f"rel_{i}",
               "start_node_element_id": f"node_{from_label}",
               "end_node_element_id": f"node_{to_label}"
            })
         
         result = {"nodes": list(nodes_map.values()), "relationships": rels_list}
      else:
         query = """
         MATCH (d:Document)<-[:PART_OF]-(c:Chunk)-[:HAS_ENTITY]->(n)-[r]->(m)
         WHERE d.patient_id IS NULL
         WITH DISTINCT labels(n) AS fromLabels, type(r) AS relType, labels(m) AS toLabels
         RETURN fromLabels, relType, toLabels
         """
         records, summary, keys = driver.execute_query(query)
         
         nodes_map = {}
         rels_list = []
         for i, record in enumerate(records):
            from_label = record["fromLabels"][0] if record["fromLabels"] else "Unknown"
            to_label = record["toLabels"][0] if record["toLabels"] else "Unknown"
            rel_type = record["relType"]
            if from_label not in nodes_map:
               nodes_map[from_label] = {"element_id": f"node_{from_label}", "labels": [from_label], "properties": {}}
            if to_label not in nodes_map:
               nodes_map[to_label] = {"element_id": f"node_{to_label}", "labels": [to_label], "properties": {}}
            rels_list.append({
               "type": rel_type,
               "properties": {},
               "element_id": f"rel_{i}",
               "start_node_element_id": f"node_{from_label}",
               "end_node_element_id": f"node_{to_label}"
            })
         result = {"nodes": list(nodes_map.values()), "relationships": rels_list}
      return result
   except Exception as e:
       logging.error(f"An error occurred schema retrieval. Error: {str(e)}")
       raise Exception(f"An error occurred schema retrieval. Error: {str(e)}")
   finally:
       if driver:
           driver.close()
