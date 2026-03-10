import logging
from langchain_core.documents import Document
import os
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_google_vertexai import ChatVertexAI
from langchain_groq import ChatGroq
from langchain_google_vertexai import HarmBlockThreshold, HarmCategory
from langchain_experimental.graph_transformers.diffbot import DiffbotGraphTransformer
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_anthropic import ChatAnthropic
from langchain_fireworks import ChatFireworks
from langchain_aws import ChatBedrock
from langchain_community.chat_models import ChatOllama
from langchain_huggingface import HuggingFacePipeline
import boto3
import google.auth
from src.shared.constants import ADDITIONAL_INSTRUCTIONS
from src.shared.llm_graph_builder_exception import LLMGraphBuilderException
import re
from typing import List
from langchain_core.callbacks.manager import CallbackManager
from src.shared.common_fn import UniversalTokenUsageHandler
from src.shared.env_utils import get_value_from_env

def get_llm(model: str):
    """Retrieve the specified language model based on the model name."""
    model = model.upper().replace('.', '_').strip()
    env_key = f"LLM_MODEL_CONFIG_{model}"
    env_value = get_value_from_env(env_key)
    
    if not env_value:
        # Generic fallback: Construct config from specific API keys if main config is missing
        if "OPENAI" in model:
            api_key = get_value_from_env("OPENAI_API_KEY")
            if api_key:
                # Format model name: OPENAI_GPT_4O -> gpt-4o, OPENAI_GPT_3_5 -> gpt-3.5-turbo
                formatted_model = model.lower().replace("openai_", "").replace("_", "-")
                if formatted_model == "gpt-3-5":
                    formatted_model = "gpt-3.5-turbo"
                env_value = f"{formatted_model},{api_key}"
            elif "AZURE" not in model: 
                 # Fallback for generic OPENAI key if specific config missing
                 env_value = f"gpt-4o,{api_key}"

        elif "DIFFBOT" in model:
            api_key = get_value_from_env("DIFFBOT_API_KEY")
            if api_key:
                env_value = f"diffbot,{api_key}"

        elif "GEMINI" in model:
            # Gemini often just needs the model name if auth is via separate Google creds, 
            # but usually users provide GOOGLE_API_KEY. The code expects just "model_name".
            # We'll default to gemini-pro if not set.
            env_value = "gemini-1.5-pro-001" 

        elif "ANTHROPIC" in model:
            api_key = get_value_from_env("ANTHROPIC_API_KEY")
            if api_key:
                # Map frontend model identifiers to Anthropic API model names
                anthropic_model_map = {
                    "ANTHROPIC_CLAUDE_4_5_SONNET": "claude-sonnet-4-20250514",
                    "ANTHROPIC_CLAUDE_4_5_HAIKU": "claude-haiku-4-20250514",
                    "ANTHROPIC_CLAUDE_4_OPUS": "claude-opus-4-20250514",
                    "ANTHROPIC_CLAUDE_3_5_SONNET": "claude-3-5-sonnet-20241022",
                }
                api_model_name = anthropic_model_map.get(model, model.lower().replace("anthropic_", "claude-").replace("_", "-"))
                env_value = f"{api_model_name},{api_key}"
        
        elif "FIREWORKS" in model:
            api_key = get_value_from_env("FIREWORKS_API_KEY")
            if api_key:
                 env_value = f"accounts/fireworks/models/{model.lower().replace('_', '.')},{api_key}"

        elif "GROQ" in model:
             api_key = get_value_from_env("GROQ_API_KEY")
             if api_key:
                  # Force a default model if only key is provided
                  formatted_model = model.lower().replace("groq_", "").replace("_", "-")
                  if formatted_model == "groq":
                      formatted_model = "llama-3.1-8b-instant"
                  env_value = f"{formatted_model},https://api.groq.com/openai/v1,{api_key}"
        
        elif "SARVAM" in model:
            api_key = get_value_from_env("SARVAM_API_KEY")
            if api_key:
                # Default to sarvam-m if no specific model requested
                formatted_model = model.lower().replace("sarvam_", "").replace("_", "-")
                if formatted_model == "sarvam":
                    formatted_model = "sarvam-m"
                env_value = f"{formatted_model},https://api.sarvam.ai/v1,{api_key}"
        
        elif "LOCAL" in model:
             if "SARVAM" in model:
                 # Point to the new indic-llm service
                 env_value = "sarvam-2b,http://indic-llm:8000/v1,no-key"
             else:
                 # Point to the local-llm-proxy service
                 env_value = "mistral-7b,http://local-llm-proxy:8090/v1,no-key"

        if env_value:
             logging.info(f"Using fallback config for {model} with discovered API Key")

    if not env_value:
        err = f"Environment variable '{env_key}' is not defined as per format or missing"
        logging.error(err)
        raise Exception(err)
    
    logging.info("Model: {}".format(env_key))
    callback_handler = UniversalTokenUsageHandler()
    callback_manager = CallbackManager([callback_handler])
    try:
        if "GEMINI" in model:
            model_name = env_value
            credentials, project_id = google.auth.default()
            llm = ChatVertexAI(
                model_name=model_name,
                credentials=credentials,
                project=project_id,
                temperature=0,
                callbacks=callback_manager,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                },
            
            )
        elif "OPENAI" in model:
            model_name, api_key = env_value.split(",")
            if "MINI" in model:
                llm= ChatOpenAI(
                api_key=api_key,
                model=model_name,
                callbacks=callback_manager,
                )
            else:
                llm = ChatOpenAI(
                api_key=api_key,
                model=model_name,
                temperature=0,
                callbacks=callback_manager,
                )

        elif "AZURE" in model:
            model_name, api_endpoint, api_key, api_version = env_value.split(",")
            llm = AzureChatOpenAI(
                api_key=api_key,
                azure_endpoint=api_endpoint,
                azure_deployment=model_name,  # takes precedence over model parameter
                api_version=api_version,
                temperature=0,
                max_tokens=None,
                timeout=None,
                callbacks=callback_manager,
            )

        elif "ANTHROPIC" in model:
            model_name, api_key = env_value.split(",")
            llm = ChatAnthropic(
                api_key=api_key, model=model_name, temperature=0, timeout=None,callbacks=callback_manager, 
            )

        elif "FIREWORKS" in model:
            model_name, api_key = env_value.split(",")
            llm = ChatFireworks(api_key=api_key, model=model_name,callbacks=callback_manager)

        elif "GROQ" in model:
            model_name, base_url, api_key = env_value.split(",")
            llm = ChatGroq(api_key=api_key, model_name=model_name, temperature=0,callbacks=callback_manager)

        elif "BEDROCK" in model:
            model_name, aws_access_key, aws_secret_key, region_name = env_value.split(",")
            bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=region_name,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
            )

            llm = ChatBedrock(
                client=bedrock_client,region_name=region_name, model_id=model_name, model_kwargs=dict(temperature=0),callbacks=callback_manager, 
            )

        elif "OLLAMA" in model:
            model_name, base_url = env_value.split(",")
            llm = ChatOllama(base_url=base_url, model=model_name,callbacks=callback_manager)

        elif "LOCAL" in model or "SARVAM" in model:
            model_name, base_url, api_key = env_value.split(",")
            llm = ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model_name,
                temperature=0,
                timeout=300,
                callbacks=callback_manager,
            )
        
        elif "SARVAM_LOCAL_2B" in model:
            model_path = env_value.split(",")[0]
            # Use data directory as base if relative path
            if not os.path.isabs(model_path):
                 model_path = os.path.join(os.getcwd(), model_path)
            
            llm = HuggingFacePipeline.from_model_id(
                model_id=model_path,
                task="text-generation",
                pipeline_kwargs={
                    "max_new_tokens": 1024,
                    "top_k": 50,
                    "temperature": 0.1,
                },
                callbacks=callback_manager,
            )

        elif "DIFFBOT" in model:
            #model_name = "diffbot"
            model_name, api_key = env_value.split(",")
            llm = DiffbotGraphTransformer(
                diffbot_api_key=api_key,
                extract_types=["entities", "facts"],
            )
            callback_handler = None
        
        else: 
            model_name, api_endpoint, api_key = env_value.split(",")
            llm = ChatOpenAI(
                api_key=api_key,
                base_url=api_endpoint,
                model=model_name,
                temperature=0,
                callbacks=callback_manager,
            )
    except Exception as e:
        err = f"Error while creating LLM '{model}': {str(e)}"
        logging.error(err)
        raise Exception(err)
 
    logging.info(f"Model created - Model Version: {model}")
    return llm, model_name, callback_handler

async def translate_text(text: str, target_lang: str, source_lang: str = "en") -> str:
    """
    Smart, cost-conscious translation:
    1. Check PostgreSQL cache for each sentence/term
    2. Only call Sarvam AI Cloud API for UNCACHED segments
    3. Cache new translations for future reuse
    """
    import httpx
    import re
    from .translation_cache import get_cached, save_to_cache, ensure_table
    from .database import SessionLocal

    if not text or not text.strip():
        return text
    if target_lang == source_lang:
        return text

    # Sarvam AI language code mapping
    SARVAM_LANG_MAP = {
        "en": "en-IN", "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN",
        "bn": "bn-IN", "mr": "mr-IN", "kn": "kn-IN", "ml": "ml-IN",
        "gu": "gu-IN", "pa": "pa-IN", "or": "od-IN",
    }

    ensure_table()
    db = SessionLocal()

    try:
        # --- Step 1: Try full-text cache first (fastest path) ---
        cached_full = get_cached(db, text.strip(), source_lang, target_lang)
        if cached_full:
            logging.info(f"[CACHE HIT] Full text: '{text[:50]}...' → {target_lang}")
            return cached_full

        # --- Step 2: Split into sentences and check cache per-sentence ---
        sentences = [s.strip() for s in re.split(r'(?<=[.!?।])\s+', text.strip()) if s.strip()]
        if not sentences:
            sentences = [text.strip()]

        translated_parts = []
        uncached_segments = []  # (index, text) pairs for API call

        for i, sentence in enumerate(sentences):
            cached = get_cached(db, sentence, source_lang, target_lang)
            if cached:
                translated_parts.append((i, cached))
                logging.info(f"[CACHE HIT] Sentence: '{sentence[:40]}...'")
            else:
                translated_parts.append((i, None))  # placeholder
                uncached_segments.append((i, sentence))

        # --- Step 3: Batch uncached segments to Sarvam AI (Clinical Intelligence Engine) ---
        if uncached_segments:
            try:
                # Use a chat model with clinical system prompt
                from langchain_core.messages import SystemMessage, HumanMessage
                
                # Enforce medical persona to prevent "Intelligence" -> "Spy" errors
                system_prompt = (
                    "You are a medical translation expert. Translate the text accurately into the target language. "
                    "Maintain strict clinical context. Example: 'Intelligence' means clinical ability, NOT espionage. "
                    "Translate for a medical professional audience."
                )

                clinical_llm = get_llm("SARVAM_SARVAM_2B" if os.getenv("APP_ENV") != "production" else "SARVAM_SARVAM_M")

                for idx, segment in uncached_segments:
                    try:
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=f"Translate to {target_lang} from {source_lang}: {segment}")
                        ]
                        response = await clinical_llm.ainvoke(messages)
                        translated = response.content.strip()
                        
                        save_to_cache(db, segment, source_lang, target_lang, translated)
                        translated_parts[idx] = (idx, translated)
                    except Exception as segment_err:
                        logging.warning(f"Clinical translation failed for segment, falling back to original: {segment_err}")
                        translated_parts[idx] = (idx, segment)
            except Exception as e:
                logging.error(f"Failed to initialize clinical translation: {e}")
                for idx, segment in uncached_segments:
                    translated_parts[idx] = (idx, segment)

        # --- Step 4: Reassemble ---
        result = " ".join(part for _, part in sorted(translated_parts, key=lambda x: x[0]))

        # Cache the full assembled translation too
        if len(sentences) > 1:
            save_to_cache(db, text.strip(), source_lang, target_lang, result)

        return result

    except Exception as e:
        logging.error(f"Translation error: {e}")
        return text
    finally:
        db.close()

def get_llm_model_name(llm):
    """Extract name of llm model from llm object"""
    for attr in ["model_name", "model", "model_id"]:
        model_name = getattr(llm, attr, None)
        if model_name:
            return model_name.lower()
    logging.info("Could not determine model name; defaulting to empty string")
    return ""

def get_combined_chunks(chunkId_chunkDoc_list, chunks_to_combine):
    combined_chunk_document_list = []
    combined_chunks_page_content = [
        "".join(
            document["chunk_doc"].page_content
            for document in chunkId_chunkDoc_list[i : i + chunks_to_combine]
        )
        for i in range(0, len(chunkId_chunkDoc_list), chunks_to_combine)
    ]
    combined_chunks_ids = [
        [
            document["chunk_id"]
            for document in chunkId_chunkDoc_list[i : i + chunks_to_combine]
        ]
        for i in range(0, len(chunkId_chunkDoc_list), chunks_to_combine)
    ]

    for i in range(len(combined_chunks_page_content)):
        combined_chunk_document_list.append(
            Document(
                page_content=combined_chunks_page_content[i],
                metadata={"combined_chunk_ids": combined_chunks_ids[i]},
            )
        )
    return combined_chunk_document_list

def get_chunk_id_as_doc_metadata(chunkId_chunkDoc_list):
    combined_chunk_document_list = [
       Document(
           page_content=document["chunk_doc"].page_content,
           metadata={"chunk_id": [document["chunk_id"]]},
       )
       for document in chunkId_chunkDoc_list
   ]
    return combined_chunk_document_list
      

async def get_graph_document_list(
    llm, combined_chunk_document_list, allowedNodes, allowedRelationship,callback_handler, additional_instructions=None
):
    if additional_instructions:
        additional_instructions = sanitize_additional_instruction(additional_instructions)
    graph_document_list = []
    token_usage = 0
    try:
        if "diffbot_api_key" in dir(llm):
            llm_transformer = llm
        else:
            supported_models = ["ChatOpenAI", "ChatVertexAI", "AzureChatOpenAI","ChatAnthropic"]
            if hasattr(llm, "get_name") and llm.get_name() in supported_models:
                node_properties = False
                relationship_properties = False
            else:
                node_properties = ["description"]
                relationship_properties = ["description"]
            llm_transformer = LLMGraphTransformer(
                llm=llm,
                node_properties=node_properties,
                relationship_properties=relationship_properties,
                allowed_nodes=allowedNodes,
                allowed_relationships=allowedRelationship,
                ignore_tool_usage=True,
                additional_instructions=ADDITIONAL_INSTRUCTIONS+ (additional_instructions if additional_instructions else "")
            )
        
        if isinstance(llm,DiffbotGraphTransformer):
            graph_document_list = llm_transformer.convert_to_graph_documents(combined_chunk_document_list)
        else:
            graph_document_list = await llm_transformer.aconvert_to_graph_documents(combined_chunk_document_list)
    except Exception as e:
       logging.error(f"Error in graph transformation: {e}", exc_info=True)
       raise LLMGraphBuilderException(f"Graph transformation failed: {str(e)}")
    finally:
        try:
            if callback_handler:
                usage = callback_handler.report()
                token_usage = usage.get("total_tokens", 0)
        except Exception as usage_err:
            logging.error(f"Error while reporting token usage: {usage_err}")

    return graph_document_list, token_usage

async def get_graph_from_llm(model, chunkId_chunkDoc_list, allowedNodes, allowedRelationship, chunks_to_combine, additional_instructions=None):
   try:
       llm, model_name,callback_handler = get_llm(model)
       logging.info(f"Using model: {model_name}")
    
       combined_chunk_document_list = get_combined_chunks(chunkId_chunkDoc_list, chunks_to_combine)
       logging.info(f"Combined {len(combined_chunk_document_list)} chunks")
    
       allowed_nodes = [node.strip() for node in allowedNodes.split(',') if node.strip()]
       logging.info(f"Allowed nodes: {allowed_nodes}")
    
       allowed_relationships = []
       if allowedRelationship:
           items = [item.strip() for item in allowedRelationship.split(',') if item.strip()]
           if len(items) % 3 != 0:
               raise LLMGraphBuilderException("allowedRelationship must be a multiple of 3 (source, relationship, target)")
           for i in range(0, len(items), 3):
               source, relation, target = items[i:i + 3]
               if source not in allowed_nodes or target not in allowed_nodes:
                   raise LLMGraphBuilderException(
                       f"Invalid relationship ({source}, {relation}, {target}): "
                       f"source or target not in allowedNodes"
                   )
               allowed_relationships.append((source, relation, target))
           logging.info(f"Allowed relationships: {allowed_relationships}")
       else:
           logging.info("No allowed relationships provided")

       graph_document_list,token_usage = await get_graph_document_list(
           llm,
           combined_chunk_document_list,
           allowed_nodes,
           allowed_relationships,
           callback_handler,
           additional_instructions,
       )
       logging.info(f"Generated {len(graph_document_list)} graph documents")
       return graph_document_list, token_usage
   except Exception as e:
       logging.error(f"Error in get_graph_from_llm: {e}", exc_info=True)
       raise LLMGraphBuilderException(f"Error in getting graph from llm: {e}")

def sanitize_additional_instruction(instruction: str) -> str:
   """
   Sanitizes additional instruction by:
   - Replacing curly braces `{}` with `[]` to prevent variable interpretation.
   - Removing potential injection patterns like `os.getenv()`, `eval()`, `exec()`.
   - Stripping problematic special characters.
   - Normalizing whitespace.
   Args:
       instruction (str): Raw additional instruction input.
   Returns:
       str: Sanitized instruction safe for LLM processing.
   """
   logging.info("Sanitizing additional instructions")
   instruction = instruction.replace("{", "[").replace("}", "]")  # Convert `{}` to `[]` for safety
   # Step 2: Block dangerous function calls
   injection_patterns = [r"os\.getenv\(", r"eval\(", r"exec\(", r"subprocess\.", r"import os", r"import subprocess"]
   for pattern in injection_patterns:
       instruction = re.sub(pattern, "[BLOCKED]", instruction, flags=re.IGNORECASE)
   # Step 4: Normalize spaces
   instruction = re.sub(r'\s+', ' ', instruction).strip()
   return instruction
HYPERTENSION_RULES = """
Specific Guidelines for HYPERTENSION (Reconciliation Vers 8):
1. Vitals: Always look for 'systolic_bp' and 'diastolic_bp'. If multiple readings exist, use the LAST one.
2. BP Categories: 
   - Normal (<120/80)
   - Elevated (120-129/<80)
   - Stage1 (130-139 or 80-89)
   - Stage2 (>=140 or >=90)
   - CrisisSuspected (>=180 or >=120)
3. Symptoms (Tri-State): headache, chest_pain, breathlessness, neurological.
4. Suspicions: diet_high_salt, sleep_poor, stress_high, tobacco_use, alcohol_high.
5. Red Flags: HRF1: CrisisSuspected, HRF2: Chest pain/breathlessness, HRF3: Neurological, HRF4: Pregnancy+Stage2/Crisis, HRF5: CKD/CVD+Stage2/Crisis.
"""

async def validate_clinical_content(model: str, text: str) -> bool:
    """
    Validates if the provided text is a clinical record (EHR, transcript, scan, lab report).
    Returns True if valid, False otherwise.
    """
    try:
        llm, _, _ = get_llm(model)
        system_msg = "You are a medical administrative assistant. Your task is to determine if the given text is a clinical record, medical transcript, prescription scan, or patient visit note. Respond with exactly 'YES' if it is a clinical/medical record, and 'NO' otherwise. No explanations."
        
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=f"Text to validate:\n\n{text[:2000]}") # Only need first 2k chars for validation
        ]
        
        response = await llm.ainvoke(messages)
        content = response.content.strip().upper()
        return "YES" in content
    except Exception as e:
        logging.error(f"Error in source validation: {e}")
        return True # Default to True in case of error to avoid blocking valid flows

HYPERTENSION_INFERENCE_RULES = """
Specific Inference Guidelines for HYPERTENSION (Reconciliation Vers 8):
1. BP Category Inference:
   - Normal: <120/80
   - Elevated: 120-129/<80
   - Stage1: 130-139 OR 80-89
   - Stage2: >=140 OR >=90
   - CrisisSuspected: >=180 OR >=120
2. Red Flag Inference (IDs):
   - HRF1: BP Category is 'CrisisSuspected'
   - HRF2: Symptoms include 'Chest Pain' or 'Severe Breathlessness'
   - HRF3: Symptoms include 'Neurological' issues (confusion, slurred speech)
   - HRF4: Patient is Pregnant AND (Stage2 or CrisisSuspected)
   - HRF5: Known Comorbidities (CKD/CVD) AND (Stage2 or CrisisSuspected)
"""

async def extract_structured_ehr_data(model: str, text: str, condition_profile: str = None):
    """
    Extract structured EHR data from text using the provided model and schema.
    Performs autonomous semantic inference for status, categories, and red flags.
    """
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic.v1 import BaseModel, Field

        llm, model_name, _ = get_llm(model)
        
        class VitalModel(BaseModel):
            name: str = Field(description="Normalized vital name (e.g., systolic_bp, heart_rate)")
            value: float = Field(description="Numeric value")
            unit: str = Field(description="Unit of measurement")
            status: str = Field(description="Inferred clinical status based on standards (e.g., 'Normal', 'Stage2')")

        class SymptomModel(BaseModel):
            name: str = Field(description="Normalized symptom name")
            status: str = Field(description="Evidence-based Tri-State: 'True', 'False', or 'Unknown'")

        class LifestyleSuspicionModel(BaseModel):
            factor: str = Field(description="Lifestyle factor (Salt, Stress, Sleep, Tobacco, Alcohol)")
            status: str = Field(description="Inferred suspicion status: 'True', 'False', or 'Unknown'")

        class EHRSchema(BaseModel):
            case_id: str = Field(description="Case ID")
            visit_date: str = Field(description="YYYY-MM-DD")
            age_group: str = Field(description="Inferred age range")
            sex: str = Field(description="Inferred sex")
            condition_name: str = Field(description="Identified primary ailment/condition (e.g., Hypertension)")
            chief_complaint: str = Field(description="Brief complaint summary (max 200 chars)")
            vitals: List[VitalModel] = Field(description="Extracted vitals with inferred statuses")
            symptoms: List[SymptomModel] = Field(description="Extracted symptoms with tri-state evidence")
            suspicions: List[LifestyleSuspicionModel] = Field(description="Inferred lifestyle risks")
            red_flag_any: bool = Field(description="True if any red flags are inferred from the clinical context")
            red_flag_list: List[str] = Field(description="List of inferred Red Flag IDs (e.g., HRF1, HRF2)")

        inference_context = ""
        if condition_profile and "hypertension" in condition_profile.lower():
            inference_context = HYPERTENSION_INFERENCE_RULES
        else:
            inference_context = "If the text relates to Hypertension, apply BP category and Red Flag IDs (HRF1-HRF5) according to medical standards."

        system_message = f"""You are a Clinical Intelligence Engine. Your task is to perform context-aware extraction and autonomous inference from patient notes.
        
        Clinical Reasoning Goals:
        1. Identification: Determine the primary ailment (condition_name).
        2. Inference: Evaluate vitals and symptoms to infer clinical statuses and categories.
        3. Risk Assessment: Determine if any Red Flags are present based on the inferred context.
        
        {inference_context}
        
        Mandatory Guidelines:
        - Use the YogNayur EHR structure.
        - Tri-State Statuses: 'True' (Clear evidence), 'False' (Explicitly denied), 'Unknown' (No mention).
        - Do not hallucinate data. If a field is missing, use 'Unknown' or appropriate defaults.
        - Chief Complaint: Synthetic summary, max 200 chars."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "Analyze and extract intelligence from this clinical text:\n\n{text}")
        ])
        
        chain = prompt | llm.with_structured_output(EHRSchema)
        result = await chain.ainvoke({"text": text})
        return result
    except Exception as e:
        logging.error(f"Error in intelligence-first structured extraction: {e}")
        return None
