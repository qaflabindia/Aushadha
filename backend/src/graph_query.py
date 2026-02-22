import logging
from neo4j import time 
from neo4j import GraphDatabase
from src.shared.common_fn import get_value_from_env
import os
import json

from src.shared.constants import GRAPH_CHUNK_LIMIT,GRAPH_QUERY,CHUNK_TEXT_QUERY,COUNT_CHUNKS_QUERY,SCHEMA_VISUALIZATION_QUERY

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


def execute_query(driver, query,document_names,doc_limit=None):
    """
    Executes a specified query using the Neo4j driver, with parameters based on the presence of a document name.

    Returns:
    tuple: Contains records, summary of the execution, and keys of the records.
    """
    try:
        if document_names:
            logging.info(f"Executing query for documents: {document_names}")
            records, summary, keys = driver.execute_query(query, document_names=document_names)
        else:
            logging.info(f"Executing query with a document limit of {doc_limit}")
            records, summary, keys = driver.execute_query(query, doc_limit=doc_limit)
        return records, summary, keys
    except Exception as e:
        error_message = f"graph_query module: Failed to execute the query. Error: {str(e)}"
        logging.error(error_message, exc_info=True)


def process_node(node):
    """
    Processes a node from a Neo4j database, extracting its ID, labels, and properties,
    while omitting certain properties like 'embedding' and 'text'.

    Returns:
    dict: A dictionary with the node's element ID, labels, and other properties,
          with datetime objects formatted as ISO strings.
    """
    try:
        labels = set(node.labels)
        labels.discard("__Entity__")
        if not labels:
            labels.add('*')
        
        node_element = {
            "element_id": node.element_id,
            "labels": list(labels),
            "properties": {}
        }
        # logging.info(f"Processing node with element ID: {node.element_id}")

        for key in node:
            if key in ["embedding", "text", "summary"]:
                continue
            value = node.get(key)
            if isinstance(value, time.DateTime):
                node_element["properties"][key] = value.isoformat()
                # logging.debug(f"Processed datetime property for {key}: {value.isoformat()}")
            else:
                node_element["properties"][key] = value

        return node_element
    except Exception as e:
        logging.error("graph_query module:An unexpected error occurred while processing the node")

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
                # logging.debug(f"No nodes found in record: {record}")
                continue

            for node in nodes:
                if node.element_id in seen_element_ids:
                    # logging.debug(f"Skipping already processed node with ID: {node.element_id}")
                    continue
                seen_element_ids.add(node.element_id)
                node_element = process_node(node) 
                node_elements.append(node_element)
                # logging.info(f"Processed node with ID: {node.element_id}")

        return node_elements
    except Exception as e:
        logging.error("graph_query module: An error occurred while extracting node elements from records")

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
                    # logging.debug(f"Skipping already processed relationship with ID: {relation.element_id}")
                    continue
                seen_element_ids.add(relation.element_id)

                try:
                    nodes = relation.nodes
                    if len(nodes) < 2:
                        logging.warning(f"Relationship with ID {relation.element_id} does not have two nodes.")
                        continue

                    relationship = {
                        "element_id": relation.element_id,
                        "type": relation.type,
                        "start_node_element_id": process_node(nodes[0])["element_id"],
                        "end_node_element_id": process_node(nodes[1])["element_id"],
                    }
                    relationships.append(relationship)

                except Exception as inner_e:
                    logging.error(f"graph_query module: Failed to process relationship with ID {relation.element_id}. Error: {inner_e}", exc_info=True)
            all_relationships.extend(relationships)
        return all_relationships
    except Exception as e:
        logging.error("graph_query module: An error occurred while extracting relationships from records", exc_info=True)


def get_completed_documents(driver):
    """
    Retrieves the names of all documents with the status 'Completed' from the database.
    """
    docs_query = "MATCH(node:Document {status:'Completed'}) RETURN node"
    
    try:
        logging.info("Executing query to retrieve completed documents.")
        records, summary, keys = driver.execute_query(docs_query)
        logging.info(f"Query executed successfully, retrieved {len(records)} records.")
        documents = [record["node"]["fileName"] for record in records]
        logging.info("Document names extracted successfully.")
        
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        documents = []
    
    return documents


async def get_graph_results(credentials, document_names, language="en", model=None):
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
        records, summary , keys = await asyncio.to_thread(execute_query, driver, query.strip(), document_names)
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

# Translation cache to avoid repeated LLM calls for the same terms
_translation_cache = {}

async def translate_graph_labels(nodes, relationships, language, model):
    """
    Translate node labels, node property 'id', and relationship types to the target language.
    Uses a simple LLM call for batch translation with caching.
    """
    lang_map = {
        "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali",
        "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam",
        "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
    }
    lang_name = lang_map.get(language, language)

    # Collect all unique terms that need translation
    terms_to_translate = set()
    for node in nodes:
        if node and "labels" in node:
            for label in node["labels"]:
                terms_to_translate.add(label)
        if node and "properties" in node:
            prop_id = node["properties"].get("id")
            if prop_id and isinstance(prop_id, str):
                terms_to_translate.add(prop_id)
    for rel in relationships:
        if rel and "type" in rel:
            terms_to_translate.add(rel["type"])

    # Check cache first, find terms needing translation
    cache_key_prefix = f"{language}:"
    uncached_terms = []
    for term in terms_to_translate:
        if f"{cache_key_prefix}{term}" not in _translation_cache:
            uncached_terms.append(term)

    # Batch translate uncached terms via LLM
    if uncached_terms:
        try:
            translations = await _batch_translate_with_llm(uncached_terms, lang_name, model)
            for original, translated in translations.items():
                _translation_cache[f"{cache_key_prefix}{original}"] = translated
        except Exception as e:
            logging.warning(f"Translation failed, using original labels: {e}")
            # Fallback: use original terms
            for term in uncached_terms:
                _translation_cache[f"{cache_key_prefix}{term}"] = term

    # Apply translations
    def get_translated(term):
        return _translation_cache.get(f"{cache_key_prefix}{term}", term)

    for node in nodes:
        if node and "labels" in node:
            node["labels"] = [get_translated(label) for label in node["labels"]]
        if node and "properties" in node:
            prop_id = node["properties"].get("id")
            if prop_id and isinstance(prop_id, str):
                node["properties"]["id"] = get_translated(prop_id)
    for rel in relationships:
        if rel and "type" in rel:
            rel["type"] = get_translated(rel["type"])

    return nodes, relationships


async def _batch_translate_with_llm(terms, target_language, model):
    """
    Translate a list of English terms to the target language using the user's selected LLM.
    Returns a dict mapping original -> translated.
    """
    from src.llm import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    import re
    
    terms_list = "\n".join([f"- {term}" for term in terms])
    prompt = f"""Translate the following English terms to {target_language}. 
Return ONLY a valid JSON object mapping each original English term to its {target_language} translation.
Do not add any explanations, markdown blocks, or surrounding text. Keep technical/medical terms transliterated if no standard translation exists.

Terms to translate:
{terms_list}

Strict Output Format:
{{"original_term": "translated_term", ...}}"""

    try:
        # Fallback to OpenAI gpt-4o if no model provided or if model is diffbot
        model_name = model if model else "openai_gpt_4o"
        if model_name.lower() == "diffbot":
            model_name = "openai_gpt_4o"
            
        llm, _, _ = get_llm(model_name)
        
        messages = [
            SystemMessage(content="You are a professional medical translator. Output valid JSON only, without any markdown formatting wrappers like ```json."),
            HumanMessage(content=prompt)
        ]
        
        # We try to enforce JSON parsing robustness natively through LLM invocation
        response = await llm.ainvoke(messages)
        result_text = response.content.strip()
        
        # Clean potential markdown formatting
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
            
        translations = json.loads(result_text)
        
        # Ensure all terms have a translation (fallback to original)
        for term in terms:
            if term not in translations:
                translations[term] = term
        return translations
    except Exception as e:
        logging.error(f"LLM translation error: {e}")
        return {term: term for term in terms}



def get_chunktext_results(credentials, document_name, page_no):
   """Retrieves chunk text, position, and page number from graph data with pagination."""
   driver = None
   try:
       logging.info("Starting chunk text query process")
       offset = 10
       skip = (page_no - 1) * offset
       limit = offset
       driver = get_graphDB_driver(credentials)  
       with driver.session(database=credentials.database) as session:
           total_chunks_result = session.run(COUNT_CHUNKS_QUERY, file_name=document_name)
           total_chunks = total_chunks_result.single()["total_chunks"]
           total_pages = (total_chunks + offset - 1) // offset  # Calculate total pages
           records = session.run(CHUNK_TEXT_QUERY, file_name=document_name, skip=skip, limit=limit)
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


def visualize_schema(credentials):
   """Retrieves graph schema"""
   driver = None
   try:
       logging.info("Starting visualizing graph schema")
       driver = get_graphDB_driver(credentials)  
       records, summary, keys = driver.execute_query(SCHEMA_VISUALIZATION_QUERY)
       nodes = records[0].get("nodes", [])
       relationships = records[0].get("relationships", [])
       result = {"nodes": nodes, "relationships": relationships}
       return result
   except Exception as e:
       logging.error(f"An error occurred schema retrieval. Error: {str(e)}")
       raise Exception(f"An error occurred schema retrieval. Error: {str(e)}")
   finally:
       if driver:
           driver.close()
