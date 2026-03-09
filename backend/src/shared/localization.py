import logging
import json
from langchain_core.messages import SystemMessage, HumanMessage

# Translation cache to avoid repeated LLM calls for the same terms
_translation_cache = {}

def clear_translation_cache():
    global _translation_cache
    _translation_cache = {}

async def translate_graph_labels(nodes, relationships, language, model):
    """
    Translate node labels, node property 'id', and relationship types to the target language.
    Uses a simple LLM call for batch translation with caching.
    """
    if not language or language == "en":
        return nodes, relationships

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
            for key in ["id", "name", "fileName", "label", "description", "title"]:
                val = node["properties"].get(key)
                if val and isinstance(val, str):
                    terms_to_translate.add(val)
    for rel in relationships:
        if rel and "type" in rel:
            terms_to_translate.add(rel["type"])

    # Check cache first
    cache_key_prefix = f"{language}:"
    uncached_terms = [t for t in terms_to_translate if f"{cache_key_prefix}{t}" not in _translation_cache]

    # Batch translate uncached terms
    if uncached_terms:
        try:
            translations = await _batch_translate_with_llm(uncached_terms, lang_name, model)
            for original, translated in translations.items():
                _translation_cache[f"{cache_key_prefix}{original}"] = translated
        except Exception as e:
            logging.warning(f"Translation failed: {e}")
            # Don't cache anything, we'll try again next time

    # Apply translations
    def get_translated(term):
        return _translation_cache.get(f"{cache_key_prefix}{term}", term)

    for node in nodes:
        if node and "labels" in node:
            if "original_labels" not in node:
                node["original_labels"] = list(node["labels"])
            node["labels"] = [get_translated(label) for label in node["labels"]]
        if node and "properties" in node:
            for key in ["id", "name", "fileName", "label", "description", "title"]:
                val = node["properties"].get(key)
                if val and isinstance(val, str):
                    node["properties"][key] = get_translated(val)
    for rel in relationships:
        if rel and "type" in rel:
            rel["type"] = get_translated(rel["type"])

    return nodes, relationships

async def translate_metadata(metadata, language, model):
    """
    Translate entity IDs and node details in the chat metadata.
    """
    if not language or language == "en":
        return metadata

    lang_map = {
        "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali",
        "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam",
        "gu": "Gujarati", "pa": "Punjabi", "or": "Odia"
    }
    lang_name = lang_map.get(language, language)

    # Collect terms from entities and node details
    terms_to_translate = set()
    
    # 1. From entities (entityids and relationshipids)
    entities = metadata.get("entities", {})
    for key in ["entityids", "relationshipids"]:
        for val in entities.get(key, []):
            if isinstance(val, str):
                terms_to_translate.add(val)

    # 2. From nodedetails (entitydetails, communitydetails)
    nodedetails = metadata.get("nodedetails", {})
    # For entitydetails, they are usually a list of dicts with 'id'
    for detail in nodedetails.get("entitydetails", []):
        if isinstance(detail, dict):
            for key in ["id", "name", "description", "label"]:
                if key in detail and isinstance(detail[key], str):
                    terms_to_translate.add(detail[key])
    
    # 3. Handle communitydetails if needed (usually just labels)
    for community in nodedetails.get("communitydetails", []):
         if isinstance(community, dict) and "label" in community:
              terms_to_translate.add(community["label"])
    
    # 4. From sources
    sources = metadata.get("sources", [])
    for source in sources:
        if isinstance(source, str):
            terms_to_translate.add(source)

    if not terms_to_translate:
        return metadata

    # Translation process
    cache_key_prefix = f"{language}:"
    uncached_terms = [t for t in terms_to_translate if f"{cache_key_prefix}{t}" not in _translation_cache]

    if uncached_terms:
        try:
            translations = await _batch_translate_with_llm(uncached_terms, lang_name, model)
            for original, translated in translations.items():
                _translation_cache[f"{cache_key_prefix}{original}"] = translated
        except Exception as e:
            logging.warning(f"Metadata translation failed: {e}")

    # Apply translations back to metadata
    def get_translated(term):
        return _translation_cache.get(f"{cache_key_prefix}{term}", term)

    # Apply to entities
    if "entities" in metadata:
        for key in ["entityids", "relationshipids"]:
            if key in metadata["entities"]:
                metadata["entities"][key] = [get_translated(t) for t in metadata["entities"][key]]

    # Apply to nodedetails
    if "nodedetails" in metadata:
        for detail in metadata["nodedetails"].get("entitydetails", []):
            if isinstance(detail, dict):
                for key in ["id", "name", "description", "label"]:
                    if key in detail and isinstance(detail[key], str):
                        detail[key] = get_translated(detail[key])
        for community in metadata["nodedetails"].get("communitydetails", []):
            if isinstance(community, dict) and "label" in community:
                community["label"] = get_translated(community["label"])
    
    # Apply to sources
    if "sources" in metadata:
        metadata["sources"] = [get_translated(s) for s in metadata["sources"]]

    return metadata

async def _batch_translate_with_llm(terms, target_language, model):
    """
    Translate a list of terms using LLM.
    """
    from src.llm import get_llm
    
    if not terms:
        return {}
        
    terms_list = "\n".join([f"- {term}" for term in terms])
    prompt = f"""Translate the following list of terms from English to {target_language}.
- Each term might be a single word, a medical term, a filename, or a technical relationship type (like PART_OF or HAS_ENTITY).
- Translate EVERY term into natural {target_language}. 
- For all-caps technical relationship types (e.g. 'PART_OF', 'HAS_ENTITY', 'SIMILAR', 'NEXT_CHUNK'), translate them into human-readable {target_language} phrases that accurately describe the relationship (e.g. 'part of' -> 'இதன் பகுதி').
- For node labels like 'Document', 'Chunk', 'Disease', translate them as well.
- Return ONLY a valid JSON object mapping each original English term to its {target_language} translation.
- No markdown, no explanations, no prefix/suffix. Just the JSON object.

Terms to translate:
{terms_list}

Strict Output Format:
{{"original_term": "translated_term", ...}}"""

    try:
        # Use Anthropic as default because OpenAI is out of quota and Gemini has credentials issues
        default_model = "anthropic_claude_4.5_sonnet"
        model_name = model if model else default_model
        if model_name.lower() == "diffbot":
            model_name = default_model
            
        llm, _, _ = get_llm(model_name)
        
        messages = [
            SystemMessage(content="You are a professional medical translator. Output valid JSON only."),
            HumanMessage(content=prompt)
        ]
        
        response = await llm.ainvoke(messages)
        result_text = response.content.strip()
        
        # Clean potential markdown
        if result_text.startswith("```"):
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            else:
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
        result_text = result_text.strip()
            
        translations = json.loads(result_text)
        
        # Fallback for missing terms
        for term in terms:
            if term not in translations:
                translations[term] = term
        return translations
    except Exception as e:
        logging.error(f"LOCALIZATION Error: LLM translation failed: {e}")
        return {term: term for term in terms}
