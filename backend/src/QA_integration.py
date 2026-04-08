import os
import json
import time
import logging

import threading
import re
from datetime import datetime
from typing import Any
from dotenv import load_dotenv

from langchain_neo4j import Neo4jVector
from langchain_neo4j import Neo4jChatMessageHistory
from langchain_neo4j import GraphCypherQAChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import EmbeddingsFilter, DocumentCompressorPipeline
from langchain_text_splitters import TokenTextSplitter
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory 
from langchain_core.callbacks import StdOutCallbackHandler, BaseCallbackHandler
from langchain_community.tools import DuckDuckGoSearchRun
from src.shared.llm_graph_builder_exception import LLMGraphBuilderException
# LangChain chat models
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_google_vertexai import ChatVertexAI
from langchain_groq import ChatGroq
from langchain_anthropic import ChatAnthropic
from langchain_fireworks import ChatFireworks
from langchain_aws import ChatBedrock
from langchain_community.chat_models import ChatOllama

# Local imports
from src.llm import get_llm
from src.shared.common_fn import load_embedding_model, track_token_usage,get_value_from_env
from src.shared.constants import (
    CHAT_SYSTEM_TEMPLATE, CHAT_TOKEN_CUT_OFF, CHAT_ENTITY_VECTOR_MODE,
    CHAT_GLOBAL_VECTOR_FULLTEXT_MODE, CHAT_SEARCH_KWARG_SCORE_THRESHOLD,CHAT_MODE_CONFIG_MAP, CHAT_DEFAULT_MODE, CHAT_GRAPH_MODE,CHAT_EMBEDDING_FILTER_SCORE_THRESHOLD, CHAT_DOC_SPLIT_SIZE, QUESTION_TRANSFORM_TEMPLATE,
    CHAT_AYUSH_MODE, AYUSH_MASTER_PROMPT, CHAT_VECTOR_MODE, CHAT_FULLTEXT_MODE
)
from src.shared.localization import translate_metadata
from src.ayush_sidecar import AyushSidecarDependencies, run_ayush_sidecar
load_dotenv() 

AYUSH_RESEARCH_ALLOWED_DOMAINS = [
    "ayush.gov.in",
    "ayushportal.nic.in",
    "ccras.nic.in",
    "ccrum.res.in",
    "ccrs.nic.in",
    "ccryn.gov.in",
    "nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "clinicaltrials.gov",
]

# ── Shared Chat Model Resolver ─────────────────────────────────────────
def resolve_chat_model(model: str | None) -> str:
    """Resolve the actual chat-capable model to use for interactive chat paths."""
    if not model:
        return get_value_from_env("DEFAULT_DIFFBOT_CHAT_MODEL", "openai_gpt_5_mini")
    if model == "diffbot":
        return get_value_from_env("DEFAULT_DIFFBOT_CHAT_MODEL", "openai_gpt_5_mini")
    return model


def _resolve_openai_runtime_config(model: str) -> tuple[str | None, str | None]:
    model_key = model.upper().replace(".", "_").strip()
    env_key = f"LLM_MODEL_CONFIG_{model_key}"
    env_value = get_value_from_env(env_key)

    if not env_value and "OPENAI" in model_key:
        api_key = get_value_from_env("OPENAI_API_KEY")
        if api_key:
            formatted_model = model_key.lower().replace("openai_", "").replace("_", "-")
            if formatted_model == "gpt-3-5":
                formatted_model = "gpt-3.5-turbo"
            elif formatted_model == "gpt-5-2":
                formatted_model = "gpt-5.2"
            env_value = f"{formatted_model},{api_key}"

    if not env_value:
        return None, None

    parts = [get_value_from_env(part.strip()) or part.strip() for part in env_value.split(",")]
    if len(parts) < 2:
        return None, None
    return parts[0], parts[1]


def _supports_openai_reasoning_effort(model_name: str) -> bool:
    lowered = (model_name or "").lower()
    return lowered.startswith("gpt-5") or lowered.startswith("o")


def _extract_openai_web_sources(response_payload: dict) -> list[str]:
    urls: list[str] = []
    for item in response_payload.get("output", []) or []:
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            for source in action.get("sources", []) or []:
                url = source.get("url")
                if url:
                    urls.append(url)
        if item.get("type") == "message":
            for content in item.get("content", []) or []:
                for annotation in content.get("annotations", []) or []:
                    if annotation.get("type") == "url_citation" and annotation.get("url"):
                        urls.append(annotation["url"])
    return list(dict.fromkeys(urls))


def _conduct_openai_ayush_research(
    disease_name: str,
    research_model: str,
    allowed_domains: list[str] | None = None,
) -> tuple[str, list[str]]:
    model_name, api_key = _resolve_openai_runtime_config(research_model)
    if not model_name or not api_key:
        logging.warning("OpenAI research config missing for model=%s", research_model)
        return "", []

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        request_payload = {
            "model": model_name,
            "tools": [
                {
                    "type": "web_search",
                    "filters": {"allowed_domains": allowed_domains or AYUSH_RESEARCH_ALLOWED_DOMAINS},
                }
            ],
            "tool_choice": "required",
            "include": ["web_search_call.action.sources"],
            "input": (
                f"Conduct web research for AYUSH clinical evidence on {disease_name}. "
                "Search only within the allowed trusted domains. "
                "Return only source-grounded findings useful for an AYUSH clinical intelligence report: "
                "triage/referral rules, disease mapping, named AYUSH interventions, exact dose, duration, "
                "study design, sample size, quantified outcomes, ADRs, DOI/PMCID, CTRI, or government references. "
                "If nothing relevant is found, return exactly 'LEC'. Do not speculate."
            ),
        }
        if _supports_openai_reasoning_effort(model_name):
            request_payload["reasoning"] = {"effort": "low"}

        response = client.responses.create(**request_payload)
        payload = response.model_dump() if hasattr(response, "model_dump") else {}
        output_text = getattr(response, "output_text", "") or payload.get("output_text", "")
        sources = _extract_openai_web_sources(payload)
        if not output_text or output_text.strip().upper() == "LEC":
            return "", sources
        return output_text.strip(), sources
    except Exception as e:
        logging.error("OpenAI AYUSH web research failed: %s", e)
        return "", []


# ── AYUSH Web Research Helper ──────────────────────────────────────────
def conduct_ayush_research(
    disease_name,
    research_model: str,
    allowed_domains: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Perform provider-native AYUSH web research when supported by the selected provider."""
    try:
        resolved_model = resolve_chat_model(research_model)
        logging.info("Conducting provider-native AYUSH research for: %s using model=%s", disease_name, resolved_model)

        if resolved_model.upper().startswith("OPENAI"):
            research_text, sources = _conduct_openai_ayush_research(
                disease_name,
                resolved_model,
                allowed_domains=allowed_domains,
            )
            if research_text:
                logging.info("OpenAI AYUSH research successful: %s characters, %s sources", len(research_text), len(sources))
            return research_text, sources

        logging.warning(
            "Provider-native web search is not implemented for selected model=%s. Returning no external findings.",
            resolved_model,
        )
        return "", []
    except Exception as e:
        logging.error(f"AYUSH Web Research failed: {e}")
        return "", []

def extract_disease_from_history(messages, llm):
    """Use LLM to identify the primary disease/condition discussed in the chat history."""
    try:
        if not messages or len(messages) <= 1:
            return None
            
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a medical assistant. Identify the primary disease or medical condition being discussed in the following conversation history. Respond ONLY with the name of the condition (e.g., 'Diabetes', 'Hypertension'). If no specific condition is identified, respond with 'None'."),
            MessagesPlaceholder(variable_name="history")
        ])
        extraction_chain = extraction_prompt | llm
        response = extraction_chain.invoke({"history": messages})
        condition = response.content.strip().strip("'\"")
        return condition if condition.lower() != "none" else None
    except Exception as e:
        logging.error(f"Failed to extract disease from history: {e}")
        return None


def extract_disease_from_question(question, llm):
    """Use the current user question only to identify the primary disease/condition."""
    try:
        if not question or not question.strip():
            return None

        extraction_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a medical assistant. Identify the primary disease or medical condition in the user's question. "
                "Respond ONLY with the name of the condition (e.g., 'Diabetes', 'Hypertension'). "
                "If the question is only a generic request like 'generate report' and no specific condition is stated, respond with 'None'.",
            ),
            ("human", "{question}"),
        ])
        extraction_chain = extraction_prompt | llm
        response = extraction_chain.invoke({"question": question})
        condition = response.content.strip().strip("'\"")
        return condition if condition.lower() != "none" else None
    except Exception as e:
        logging.error(f"Failed to extract disease from question: {e}")
        return None

def fetch_patient_severity_context(graph, patient_id):
    """Retrieve measurements and symptoms for a patient to provide severity context."""
    if not patient_id:
        return ""
    try:
        # Query for measurements and symptoms associated with the patient
        query = """
        MATCH (e:__Entity__)
        WHERE e.patient_id = $pid AND (labels(e) CONTAINS 'Measurement' OR labels(e) CONTAINS 'Symptom')
        RETURN labels(e)[1] as type, e.id as detail, e.description as description
        """
        results = graph.query(query, {"pid": patient_id})
        if not results:
            return ""
            
        context_parts = ["### Patient Severity & Clinical Data:"]
        for res in results:
            detail = res['detail'].split('_')[-1] if '_' in res['detail'] else res['detail']
            desc = f" ({res['description']})" if res['description'] else ""
            context_parts.append(f"- {res['type']}: {detail}{desc}")
            
        return "\n".join(context_parts)
    except Exception as e:
        logging.warning(f"Failed to fetch severity context: {e}")
        return ""

EMBEDDING_MODEL = get_value_from_env("EMBEDDING_MODEL", "sentence_transformer")

_session_history_lock = threading.Lock()  # Fix #9: module-level lock for SessionChatHistory

class SessionChatHistory:
    history_dict = {}

    @classmethod
    def get_chat_history(cls, session_id):
        """Retrieve or create chat message history for a given session ID."""
        with _session_history_lock:  # guard check-then-act on shared class dict
            if session_id not in cls.history_dict:
                logging.info(f"Creating new ChatMessageHistory Local for session ID: {session_id}")
                cls.history_dict[session_id] = ChatMessageHistory()
            else:
                logging.info(f"Retrieved existing ChatMessageHistory Local for session ID: {session_id}")
            return cls.history_dict[session_id]

class CustomCallback(BaseCallbackHandler):

    def __init__(self):
        self.transformed_question = None
    
    def on_llm_end(
        self,response, **kwargs: Any
    ) -> None:
        logging.info("question transformed")
        self.transformed_question = response.generations[0][0].text.strip()

def get_history_by_session_id(session_id):
    try:
        return SessionChatHistory.get_chat_history(session_id)
    except Exception as e:
        logging.error(f"Failed to get history for session ID '{session_id}': {e}")
        raise

def get_total_tokens(ai_response, llm):
    try:
        if isinstance(llm, (ChatOpenAI, AzureChatOpenAI, ChatFireworks, ChatGroq)):
            total_tokens = ai_response.response_metadata.get('token_usage', {}).get('total_tokens', 0)
        
        elif isinstance(llm, ChatVertexAI):
            total_tokens = ai_response.response_metadata.get('usage_metadata', {}).get('prompt_token_count', 0)
        
        elif isinstance(llm, ChatBedrock):
            total_tokens = ai_response.response_metadata.get('usage', {}).get('total_tokens', 0)
        
        elif isinstance(llm, ChatAnthropic):
            input_tokens = int(ai_response.response_metadata.get('usage', {}).get('input_tokens', 0))
            output_tokens = int(ai_response.response_metadata.get('usage', {}).get('output_tokens', 0))
            total_tokens = input_tokens + output_tokens
        
        elif isinstance(llm, ChatOllama):
            total_tokens = ai_response.response_metadata.get("prompt_eval_count", 0)
        
        else:
            logging.warning(f"Unrecognized language model: {type(llm)}. Returning 0 tokens.")
            total_tokens = 0

    except Exception as e:
        logging.error(f"Error retrieving total tokens: {e}")
        total_tokens = 0

    return total_tokens

def clear_chat_history(graph, session_id,local=False):
    try:
        if not local:
            history = Neo4jChatMessageHistory(
                graph=graph,
                session_id=session_id
            )
        else:
            history = get_history_by_session_id(session_id)
        
        history.clear()

        return {
            "session_id": session_id, 
            "message": "The chat history has been cleared.", 
            "user": "chatbot"
        }
    
    except Exception as e:
        logging.error(f"Error clearing chat history for session {session_id}: {e}")
        return {
            "session_id": session_id, 
            "message": "Failed to clear chat history.", 
            "user": "chatbot"
        }

def get_sources_and_chunks(sources_used, docs):
    chunkdetails_list = []
    sources_used_set = set(sources_used)
    seen_ids_and_scores = set()  

    for doc in docs:
        try:
            source = doc.metadata.get("source")
            chunkdetails = doc.metadata.get("chunkdetails", [])

            if source in sources_used_set:
                for chunkdetail in chunkdetails:
                    id = chunkdetail.get("id")
                    score = round(chunkdetail.get("score", 0), 4)

                    id_and_score = (id, score)

                    if id_and_score not in seen_ids_and_scores:
                        seen_ids_and_scores.add(id_and_score)
                        chunkdetails_list.append({**chunkdetail, "score": score})

        except Exception as e:
            logging.error(f"Error processing document: {e}")

    result = {
        'sources': sources_used,
        'chunkdetails': chunkdetails_list,
    }
    return result

def get_rag_chain(llm, system_template=CHAT_SYSTEM_TEMPLATE):
    try:
        question_answering_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                MessagesPlaceholder(variable_name="messages"),
                (
                    "human",
                    "User question: {input}"
                ),
            ]
        )

        question_answering_chain = question_answering_prompt | llm

        return question_answering_chain

    except Exception as e:
        logging.error(f"Error creating RAG chain: {e}")
        raise

def format_documents(documents, model,chat_mode_settings):
    prompt_token_cutoff = None
    for model_names, value in CHAT_TOKEN_CUT_OFF.items():
        if model in model_names:
            prompt_token_cutoff = value
            break
    if prompt_token_cutoff is None:  # Fix #24: warn instead of silently using 4
        logging.warning(f"[format_documents] Model '{model}' not found in CHAT_TOKEN_CUT_OFF — defaulting to 10.")
        prompt_token_cutoff = 10

    # Fix: Safely access doc.state as it might be missing if EmbeddingsFilter is bypassed.
    sorted_documents = sorted(documents, key=lambda doc: getattr(doc, 'state', {}).get("query_similarity_score", 0), reverse=True)
    sorted_documents = sorted_documents[:prompt_token_cutoff]

    formatted_docs = list()
    sources = set()
    entities = dict()
    global_communities = list()


    for doc in sorted_documents:
        try:
            source = doc.metadata.get('source', "unknown")
            sources.add(source)
            if 'entities' in doc.metadata:
                if chat_mode_settings["mode"] == CHAT_ENTITY_VECTOR_MODE:
                    entity_ids = [entry['entityids'] for entry in doc.metadata['entities'] if 'entityids' in entry]
                    entities.setdefault('entityids', set()).update(entity_ids)
                else:
                    if 'entityids' in doc.metadata['entities']:
                        entities.setdefault('entityids', set()).update(doc.metadata['entities']['entityids'])
                    if 'relationshipids' in doc.metadata['entities']:
                        entities.setdefault('relationshipids', set()).update(doc.metadata['entities']['relationshipids'])
                
            if 'communitydetails' in doc.metadata:
                existing_ids = {entry['id'] for entry in global_communities}
                new_entries = [entry for entry in doc.metadata["communitydetails"] if entry['id'] not in existing_ids]
                global_communities.extend(new_entries)

            formatted_doc = (
                "Document start\n"
                f"This Document belongs to the source {source}\n"
                f"Content: {doc.page_content}\n"
                "Document end\n"
            )
            formatted_docs.append(formatted_doc)
        
        except Exception as e:
            logging.error(f"Error formatting document: {e}")
    
    return "\n\n".join(formatted_docs), sources,entities,global_communities

def process_documents(docs, question, messages, llm, model,chat_mode_settings):
    start_time = time.time()
    logging.info(f"Processing {len(docs)} documents")
    for i, doc in enumerate(docs):
        score = getattr(doc, 'state', {}).get("query_similarity_score")
        if score is None:
            # Try to get from metadata if it's there (sometimes it's in metadata.score or similar)
            score = doc.metadata.get("score")
        logging.info(f"Doc {i}: score={score}, source={doc.metadata.get('source')}, content_preview='{doc.page_content[:100]}...'")
    
    try:
        formatted_docs, sources, entitydetails, communities = format_documents(docs, model,chat_mode_settings)
        
        rag_chain = get_rag_chain(llm=llm)
        
        ai_response = rag_chain.invoke({
            "messages": messages[:-1],
            "context": formatted_docs,
            "input": question
        })

        result = {'sources': list(), 'nodedetails': dict(), 'entities': dict()}
        node_details = {"chunkdetails":list(),"entitydetails":list(),"communitydetails":list()}
        entities = {'entityids':list(),"relationshipids":list()}

        if chat_mode_settings["mode"] == CHAT_ENTITY_VECTOR_MODE:
            node_details["entitydetails"] = entitydetails

        elif chat_mode_settings["mode"] == CHAT_GLOBAL_VECTOR_FULLTEXT_MODE:
            node_details["communitydetails"] = communities
        else:
            sources_and_chunks = get_sources_and_chunks(sources, docs)
            result['sources'] = sources_and_chunks['sources']
            node_details["chunkdetails"] = sources_and_chunks["chunkdetails"]
            entities.update(entitydetails)

        result["nodedetails"] = node_details
        result["entities"] = entities

        content = ai_response.content
        total_tokens = get_total_tokens(ai_response, llm)
        
        predict_time = time.time() - start_time
        logging.info(f"Final response predicted in {predict_time:.2f} seconds")

    except Exception as e:
        logging.error(f"Error processing documents: {e}")
        raise
    
    return content, result, total_tokens, formatted_docs

def retrieve_documents(doc_retriever, messages):

    start_time = time.time()
    try:
        handler = CustomCallback()
        docs = doc_retriever.invoke({"messages": messages},{"callbacks":[handler]})
        if docs:
            logging.info(f"Successfully retrieved {len(docs)} documents")
        else:
            logging.info("No documents retrieved from doc_retriever.invoke")
        transformed_question = handler.transformed_question
        if transformed_question:
            logging.info(f"Transformed question : {transformed_question}")
        doc_retrieval_time = time.time() - start_time
        logging.info(f"Documents retrieved in {doc_retrieval_time:.2f} seconds")
        
    except Exception as e:
        error_message = f"Error during document retrieval: {type(e).__name__}: {str(e)}"
        logging.error(error_message, exc_info=True)
        docs = None
        transformed_question = None

    
    return docs,transformed_question

def create_document_retriever_chain(llm, retriever, mode=None):
    try:
        logging.info("Starting to create document retriever chain")

        query_transform_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUESTION_TRANSFORM_TEMPLATE),
                MessagesPlaceholder(variable_name="messages")
            ]
        )

        output_parser = StrOutputParser()

        splitter = TokenTextSplitter(chunk_size=CHAT_DOC_SPLIT_SIZE, chunk_overlap=0)
        EMBEDDING_FUNCTION , _ = load_embedding_model(EMBEDDING_MODEL) 
        # Fix: Only apply EmbeddingsFilter for simple vector/fulltext modes. 
        # Aggregated modes (graph, entity, global) return complex text that fails fixed thresholding.
        use_filter = mode in [CHAT_VECTOR_MODE, CHAT_FULLTEXT_MODE]
        
        if use_filter:
            embeddings_filter = EmbeddingsFilter(
                embeddings=EMBEDDING_FUNCTION,
                similarity_threshold=CHAT_EMBEDDING_FILTER_SCORE_THRESHOLD
            )
            pipeline_transformers = [splitter, embeddings_filter]
        else:
            pipeline_transformers = [splitter]

        pipeline_compressor = DocumentCompressorPipeline(
            transformers=pipeline_transformers
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=pipeline_compressor, base_retriever=retriever
        )

        query_transforming_retriever_chain = RunnableBranch(
            (
                lambda x: len(x.get("messages", [])) == 1,
                (lambda x: x["messages"][-1].content) | compression_retriever,
            ),
            query_transform_prompt | llm | output_parser | compression_retriever,
        ).with_config(run_name="chat_retriever_chain")

        logging.info("Successfully created document retriever chain")
        return query_transforming_retriever_chain

    except Exception as e:
        logging.error(f"Error creating document retriever chain: {e}", exc_info=True)
        raise

def initialize_neo4j_vector(graph, chat_mode_settings, document_names=None, patient_id=None):
    try:
        retrieval_query = chat_mode_settings.get("retrieval_query")
        index_name = chat_mode_settings.get("index_name")
        keyword_index = chat_mode_settings.get("keyword_index", "")
        node_label = chat_mode_settings.get("node_label")
        embedding_node_property = chat_mode_settings.get("embedding_node_property")
        text_node_properties = chat_mode_settings.get("text_node_properties")


        if not retrieval_query or not index_name:
            raise ValueError("Required settings 'retrieval_query' or 'index_name' are missing.")
        
        # Inject patient_id into retrieval_query directly to avoid 'params' error in search
        if patient_id:
            retrieval_query = retrieval_query.replace('$patient_id', f"'{patient_id}'")
        else:
            retrieval_query = retrieval_query.replace('$patient_id', "NULL")

        # Inject document_names into retrieval_query directly (similar to patient_id)
        if document_names:
            # Format list for Cypher: ['file1.pdf', 'file2.pdf']
            doc_names_cypher = json.dumps(document_names)
            retrieval_query = retrieval_query.replace('$document_names', doc_names_cypher)
        else:
            retrieval_query = retrieval_query.replace('$document_names', "[]")

        EMBEDDING_FUNCTION , _ = load_embedding_model(EMBEDDING_MODEL) 
        if keyword_index:
            neo_db = Neo4jVector.from_existing_graph(
                embedding=EMBEDDING_FUNCTION,
                index_name=index_name,
                retrieval_query=retrieval_query,
                graph=graph,
                search_type="hybrid",
                node_label=node_label,
                embedding_node_property=embedding_node_property,
                text_node_properties=text_node_properties,
                keyword_index_name=keyword_index
            )
            logging.info(f"Successfully retrieved Neo4jVector Fulltext index '{index_name}' and keyword index '{keyword_index}'")
        else:
            neo_db = Neo4jVector.from_existing_graph(
                embedding=EMBEDDING_FUNCTION,
                index_name=index_name,
                retrieval_query=retrieval_query,
                graph=graph,
                node_label=node_label,
                embedding_node_property=embedding_node_property,
                text_node_properties=text_node_properties
            )
            logging.info(f"Successfully retrieved Neo4jVector index '{index_name}'")
    except Exception as e:
        index_name = chat_mode_settings.get("index_name")
        logging.error(f"Error retrieving Neo4jVector index {index_name} : {e}")
        raise
    return neo_db

def create_retriever(neo_db, document_names, chat_mode_settings, search_k, score_threshold, ef_ratio, patient_id=None):
    search_kwargs = {
        'k': search_k,
        'effective_search_ratio': ef_ratio,
        'score_threshold': score_threshold
    }
    
    if document_names and chat_mode_settings["document_filter"]:
        search_kwargs['filter'] = {'fileName': {'$in': document_names}}
        log_msg = f"Successfully created retriever with k={search_k}, score_threshold={score_threshold} for documents {document_names}"
    else:
        log_msg = f"Successfully created retriever with k={search_k}, score_threshold={score_threshold}"

    # search_kwargs['params'] = {'patient_id': patient_id}
    if patient_id:
        log_msg += f" (patient_id: {patient_id})"

    retriever = neo_db.as_retriever(
        search_kwargs=search_kwargs
    )
    logging.info(log_msg)
    return retriever

def get_neo4j_retriever(graph, document_names,chat_mode_settings, score_threshold=CHAT_SEARCH_KWARG_SCORE_THRESHOLD, patient_id=None):
    try:

        neo_db = initialize_neo4j_vector(graph, chat_mode_settings, document_names=document_names, patient_id=patient_id)
        # document_names= list(map(str.strip, json.loads(document_names)))
        search_k = chat_mode_settings["top_k"]
        ef_ratio = get_value_from_env("EFFECTIVE_SEARCH_RATIO", 5, "int")
        retriever = create_retriever(neo_db, document_names, chat_mode_settings, search_k, score_threshold, ef_ratio, patient_id=patient_id)
        return retriever
    except Exception as e:
        index_name = chat_mode_settings.get("index_name")
        logging.error(f"Error retrieving Neo4jVector index  {index_name} or creating retriever: {e}")
        raise Exception(f"An error occurred while retrieving the Neo4jVector index or creating the retriever. Please drop and create a new vector index '{index_name}': {e}") from e 


def setup_chat(model, graph, document_names, chat_mode_settings, patient_id=None):
    start_time = time.time()
    try:
        model = resolve_chat_model(model)
        
        llm, model_name, _ = get_llm(model=model)
        logging.info(f"Model called in chat: {model} (version: {model_name})")

        retriever = get_neo4j_retriever(graph=graph, chat_mode_settings=chat_mode_settings, document_names=document_names, patient_id=patient_id)
        mode = chat_mode_settings.get("mode")
        doc_retriever = create_document_retriever_chain(llm, retriever, mode=mode)
        
        chat_setup_time = time.time() - start_time
        logging.info(f"Chat setup completed in {chat_setup_time:.2f} seconds")
        
    except Exception as e:
        logging.error(f"Error during chat setup: {e}", exc_info=True)
        raise
    
    return llm, doc_retriever, model_name

async def process_chat_response(messages, history, question, model, graph, document_names, chat_mode_settings, email=None, uri=None, language="en", patient_id=None):
    try:
        if get_value_from_env("TRACK_TOKEN_USAGE", "false", "bool"):
            try:
                track_token_usage(email, uri, 0, model)
            except LLMGraphBuilderException as e:
                logging.error(str(e))
                raise RuntimeError(str(e))
        llm, doc_retriever, model_version = setup_chat(model, graph, document_names, chat_mode_settings, patient_id=patient_id)
        
        docs,transformed_question = retrieve_documents(doc_retriever, messages)  

        if docs:
            content, result, total_tokens,formatted_docs = process_documents(docs, question, messages, llm, model, chat_mode_settings)
            
            # Translate metadata (entities and nodedetails)
            if language and language != "en":
                result = await translate_metadata(result, language, model)
                
            if get_value_from_env("TRACK_TOKEN_USAGE", "false", "bool"):
                latest_token = track_token_usage(email=email, uri=uri, usage=total_tokens, last_used_model=model)
                logging.info(f"Total token usage {latest_token} for user {email} ")
        else:
            content = "I couldn't find any relevant documents to answer your question."
            result = {"sources": list(), "nodedetails": list(), "entities": list()}
            total_tokens = 0
            formatted_docs = ""
        
        ai_response = AIMessage(content=content)
        messages.append(ai_response)

        summarization_thread = threading.Thread(target=summarize_and_log, args=(history, messages, llm))
        summarization_thread.start()
        logging.info("Summarization thread started.")
        # summarize_and_log(history, messages, llm)
        metric_details = {"question":question,"contexts":formatted_docs,"answer":content}
        return {
            "session_id": "",  
            "message": content,
            "info": {
                # "metrics" : metrics,
                "sources": result["sources"],
                "model": model_version,
                "nodedetails": result["nodedetails"],
                "total_tokens": total_tokens,
                "response_time": 0,
                "mode": chat_mode_settings["mode"],
                "entities": result["entities"],
                "metric_details": metric_details,
            },
            
            "user": "chatbot"
        }
    
    except Exception as e:
        logging.exception(f"Error processing chat response at {datetime.now()}: {str(e)}")
        return {
            "session_id": "",
            "message": "Something went wrong",
            "info": {
                "metrics" : [],
                "sources": [],
                "nodedetails": [],
                "total_tokens": 0,
                "response_time": 0,
                "error": f"{type(e).__name__}: {str(e)}",
                "mode": chat_mode_settings["mode"],
                "entities": [],
                "metric_details": {},
            },
            "user": "chatbot"
        }

def summarize_and_log(history, stored_messages, llm):
    logging.info("Starting summarization in a separate thread.")
    if not stored_messages:
        logging.info("No messages to summarize.")
        return False

    try:
        start_time = time.time()

        summarization_prompt = ChatPromptTemplate.from_messages(
            [
                MessagesPlaceholder(variable_name="chat_history"),
                (
                    "human",
                    "Summarize the above chat messages into a concise message, focusing on key points and relevant details that could be useful for future conversations. Exclude all introductions and extraneous information."
                ),
            ]
        )
        summarization_chain = summarization_prompt | llm

        summary_message = summarization_chain.invoke({"chat_history": stored_messages})

        with _session_history_lock:  # Fix #5: use module-level lock, not a new instance per call
            history.clear()
            history.add_user_message("Our current conversation summary till now")
            history.add_message(summary_message)

        history_summarized_time = time.time() - start_time
        logging.info(f"Chat History summarized in {history_summarized_time:.2f} seconds")

        return True

    except Exception as e:
        logging.error(f"An error occurred while summarizing messages: {e}", exc_info=True)
        return False 
    
def create_graph_chain(model, graph):
    try:
        logging.info(f"Graph QA Chain using LLM model: {model}")

        llm,model_name, _ = get_llm(model) 
        graph_chain = GraphCypherQAChain.from_llm(
            llm=llm,
            graph=graph,
            verbose=True,
            return_intermediate_steps=True,
            validate_cypher=True,
            allow_dangerous_requests=True
        )

        logging.info("GraphCypherQAChain instance created successfully.")
        return graph_chain,llm,model_name

    except Exception as e:
        logging.error(f"An error occurred while creating the GraphCypherQAChain instance. : {e}")
        raise  # Fix #2: propagate so caller tuple-unpack doesn't crash on None

def get_graph_response(graph_chain, question):
    try:
        cypher_res = graph_chain.invoke({"query": question})

        response = cypher_res.get("result")
        cypher_query = ""
        context = []

        for step in cypher_res.get("intermediate_steps", []):
            if "query" in step:
                cypher_string = step["query"]
                cypher_query = cypher_string.replace("cypher\n", "").replace("\n", " ").strip()
            elif "context" in step:
                context = step["context"]
        return {
            "response": response,
            "cypher_query": cypher_query,
            "context": context
        }

    except Exception as e:
        logging.error(f"An error occurred while getting the graph response : {e}")
        raise  # Fix #3: propagate so caller .get() doesn't crash on None

async def process_graph_response(model, graph, question, messages, history, language="en", patient_id=None):
    model_version = model  # Fix #4: initialize before try so except block can safely reference it
    try:
        if patient_id:
            question = f"For patient with ID '{patient_id}': {question}"
        graph_chain, llm, model_version = create_graph_chain(model, graph)

        graph_response = get_graph_response(graph_chain, question)

        ai_response_content = graph_response.get("response", "Something went wrong")
        ai_response = AIMessage(content=ai_response_content)

        messages.append(ai_response)
        summarization_thread = threading.Thread(target=summarize_and_log, args=(history, messages, llm))
        summarization_thread.start()
        logging.info("Summarization thread started.")

        # Translate context if needed (it often contains node/rel info)
        if language and language != "en":
            # Fix #1: await the coroutine first, then call .get() on the resulting dict
            translated = await translate_metadata({"context": graph_response.get("context", [])}, language, model)
            graph_response["context"] = translated.get("context", [])

        metric_details = {"question": question, "contexts": graph_response.get("context", ""), "answer": ai_response_content}
        result = {
            "session_id": "",
            "message": ai_response_content,
            "info": {
                "model": model_version,
                "cypher_query": graph_response.get("cypher_query", ""),
                "context": graph_response.get("context", ""),
                "mode": "graph",
                "response_time": 0,
                "metric_details": metric_details,
            },
            "user": "chatbot"
        }

        return result

    except Exception as e:
        logging.exception(f"Error processing graph response at {datetime.now()}: {str(e)}")
        return {
            "session_id": "",
            "message": "Something went wrong",
            "info": {
                "model": model_version,  # now always defined
                "cypher_query": "",
                "context": "",
                "mode": "graph",
                "response_time": 0,
                "error": f"{type(e).__name__}: {str(e)}"
            },
            "user": "chatbot"
        }

async def process_ayush_response(model: str, graph, document_names: list, question: str, messages: list, history, session_id: str, language: str = "en", patient_id: str = None) -> dict:
    deps = AyushSidecarDependencies(
        resolve_chat_model=resolve_chat_model,
        get_llm=get_llm,
        extract_disease_from_question=extract_disease_from_question,
        extract_disease_from_history=extract_disease_from_history,
        fetch_patient_severity_context=fetch_patient_severity_context,
        get_chat_mode_settings=get_chat_mode_settings,
        get_neo4j_retriever=get_neo4j_retriever,
        create_document_retriever_chain=create_document_retriever_chain,
        retrieve_documents=retrieve_documents,
        conduct_ayush_research=conduct_ayush_research,
        get_total_tokens=get_total_tokens,
        translate_metadata=translate_metadata,
    )
    return await run_ayush_sidecar(
        deps=deps,
        model=model,
        graph=graph,
        document_names=document_names or [],
        question=question,
        messages=messages,
        history=history,
        session_id=session_id,
        language=language,
        patient_id=patient_id,
    )
    # Fix #6: removed unreachable `return chat_mode_settings` — both try and except already return

def create_neo4j_chat_message_history(graph, session_id, write_access=True):
    """
    Creates and returns a Neo4jChatMessageHistory instance.

    """
    try:
        if write_access: 
            history = Neo4jChatMessageHistory(
                graph=graph,
                session_id=session_id
            )
            return history
        
        history = get_history_by_session_id(session_id)
        return history

    except Exception as e:
        logging.error(f"Error creating Neo4jChatMessageHistory: {e}")
        raise 

def get_chat_mode_settings(mode,settings_map=CHAT_MODE_CONFIG_MAP):
    default_settings = settings_map[CHAT_DEFAULT_MODE]
    try:
        chat_mode_settings = settings_map.get(mode, default_settings)
        chat_mode_settings["mode"] = mode
        
        logging.info(f"Chat mode settings: {chat_mode_settings}")
    
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise

    return chat_mode_settings

async def QA_RAG(graph, model, question, document_names, session_id, mode, write_access=True, email=None, uri=None, language="en", patient_id=None):
    logging.info(f"Chat Mode: {mode}")
    
    # ── Intent-based Mode Override ─────────────────────────────────────────
    # Detect if the query is asking for an Ayush research report (e.g. "Generate Ayush clinical report")
    # If so, override mode to CHAT_AYUSH_MODE regardless of frontend flag.
    ayush_keywords = ["ayush", "clinical research", "research report", "clinical report", "ayush report"]
    if any(kw in question.lower() for kw in ayush_keywords):
        if mode != CHAT_AYUSH_MODE:
            logging.info(f"AYUSH intent detected. Overriding mode from '{mode}' to '{CHAT_AYUSH_MODE}'")
            mode = CHAT_AYUSH_MODE

    history = create_neo4j_chat_message_history(graph, session_id, write_access)
    messages = history.messages

    user_question = HumanMessage(content=question)
    messages.append(user_question)

    if mode == CHAT_GRAPH_MODE:
        result = await process_graph_response(model, graph, question, messages, history, language=language, patient_id=patient_id)
    elif mode == CHAT_AYUSH_MODE:
        # Fix #15: parse document_names here (same as the else branch) so process_ayush_response
        # always receives a list, never a raw JSON string
        if document_names and isinstance(document_names, str):
            document_names = list(map(str.strip, json.loads(document_names)))
        result = await process_ayush_response(model, graph, document_names, question, messages, history, session_id, language=language, patient_id=patient_id)
    else:
        chat_mode_settings = get_chat_mode_settings(mode=mode)
        if document_names and isinstance(document_names, str):
            document_names = list(map(str.strip, json.loads(document_names)))
        else:
            document_names = []
        
        if document_names and not chat_mode_settings["document_filter"]:
            result =  {
                "session_id": "",  
                "message": "Please deselect all documents in the table before using this chat mode",
                "info": {
                    "sources": [],
                    "model": "",
                    "nodedetails": [],
                    "total_tokens": 0,
                    "response_time": 0,
                    "mode": chat_mode_settings["mode"],
                    "entities": [],
                    "metric_details": [],
                },
                "user": "chatbot"
            }
        else:
            result = await process_chat_response(messages,history, question, model, graph, document_names,chat_mode_settings, email, uri, language=language, patient_id=patient_id)

    result["session_id"] = session_id
    
    return result
