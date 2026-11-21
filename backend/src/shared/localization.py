import logging
import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from src.translation_cache import TranslationCache, get_cached_batch
from src.database import SessionLocal
from sqlalchemy import func

# Local fallback cache for within-request efficiency
_request_cache = {}

# Scripts where an English word coming back unchanged means "not translated"
_NON_LATIN_LANGS = {"hi", "ta", "te", "bn", "mr", "kn", "ml", "gu", "pa", "or", "as", "ur",
                    "zh", "ja", "ko", "ar", "ru"}
_LANG_NAMES = {
    "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali", "mr": "Marathi",
    "kn": "Kannada", "ml": "Malayalam", "gu": "Gujarati", "pa": "Punjabi", "or": "Odia",
    "as": "Assamese", "ur": "Urdu",
}
_FILE_NAME = re.compile(r"\.(pdf|docx?|txt|json|csv|md|png|jpe?g)$", re.IGNORECASE)
_LLM_CHUNK = 40  # terms per LLM call, so long graphs don't overflow one JSON reply
_MAX_TERM = 200  # longer texts (e.g. chunk text) are content, not labels: left as they are
_CACHED_RUBBISH = [
    "intended translation", "maybe", "wait", "user wrote", "medical term",
    "okay,", "let's", "i need to", "user wants", "translate", "translation",
    "into tamil", "into hindi", "sure,", "here is", "i think", "medical platform",
    "the phrase", "means", "is a", "next part", "tackle this", "உருப்படி உள்ளது",
    "அடுத்த பகுதி", "தொடர்புடையது", "குறிப்பிடப்பட்டுள்ளது",
]


def clear_translation_cache():
    global _request_cache
    _request_cache = {}


def _keep_as_is(term: str) -> bool:
    """Internal labels, file names and long content are never translated."""
    t = term.strip()
    return (
        not t
        or len(t) > _MAX_TERM
        or t == "*"
        or (t.startswith("__") and t.endswith("__"))
        or bool(_FILE_NAME.search(t))
        or not re.search(r"[A-Za-z]", t)
    )


def _is_untranslated(term: str, translated: str, language: str) -> bool:
    """A cached value that is filler text, or English left as it was."""
    low = translated.lower()
    if language not in ("en", "fr", "de", "es"):
        if any(i in low for i in _CACHED_RUBBISH):
            return True
        if len(re.findall(r"\b(the|is|at|which|on|for|of|to|and|a|an)\b", low)) > 2:
            return True
    return language in _NON_LATIN_LANGS and translated.strip().lower() == term.strip().lower()


def _store(db, term: str, language: str, translated: str) -> None:
    """Insert, or replace an earlier value that was never really translated."""
    row = (
        db.query(TranslationCache)
        .filter(
            func.lower(TranslationCache.source_text) == term.lower().strip(),
            TranslationCache.source_lang == "en",
            TranslationCache.target_lang == language,
        )
        .first()
    )
    if row:
        row.translated_text = translated
    else:
        db.add(TranslationCache(source_text=term.strip(), source_lang="en",
                                target_lang=language, translated_text=translated))
    db.commit()


async def translate_terms(terms, language, model=None) -> dict:
    """Translate short display terms (graph labels, entity names, relationship types).

    Incremental: a term is looked up in the in-process cache, then in the
    translation_cache table; only terms never translated before (or whose cached value
    was filler or plain English) go to the LLM, in chunks, and each result is saved, so
    every new term costs one LLM translation and is served from the cache after that.
    Failed or rejected translations are not saved, so they are retried next time.
    Returns {term: translation}; a term that could not be translated maps to itself.
    """
    unique = [t for t in dict.fromkeys(terms) if isinstance(t, str)]
    if not language or language == "en":
        return {t: t for t in unique}

    prefix = f"{language}:"
    result, pending = {}, []
    for t in unique:
        if _keep_as_is(t):
            result[t] = t
        elif prefix + t in _request_cache:
            result[t] = _request_cache[prefix + t]
        else:
            pending.append(t)
    if not pending:
        return result

    db = SessionLocal()
    try:
        cached = get_cached_batch(db, pending, "en", language)
        misses = []
        for t in pending:
            value = cached.get(t)
            if value and not _is_untranslated(t, value, language):
                _request_cache[prefix + t] = value
                result[t] = value
            else:
                misses.append(t)

        lang_name = _LANG_NAMES.get(language, language)
        for i in range(0, len(misses), _LLM_CHUNK):
            chunk = misses[i:i + _LLM_CHUNK]
            translations = await _batch_translate_with_llm(chunk, lang_name, model)
            for t in chunk:
                value = translations.get(t)
                if isinstance(value, str) and value.strip() and not _is_untranslated(t, value, language):
                    _request_cache[prefix + t] = value
                    _store(db, t, language, value)
                    result[t] = value
        if misses:
            done = sum(1 for t in misses if result.get(t, t) != t)
            logging.info("Translated %s of %s new terms to %s", done, len(misses), language)
    except Exception as e:
        logging.warning(f"Term translation to {language} failed: {e}")
    finally:
        db.close()

    for t in unique:
        result.setdefault(t, t)
    return result

async def translate_graph_labels(nodes, relationships, language, model):
    """
    Translate node labels, node property 'id', and relationship types to the target language.
    Uses a simple LLM call for batch translation with caching.
    """
    if not language or language == "en":
        return nodes, relationships

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
        if rel and "properties" in rel:
            # RELATIONSHIP PROPERTY SELECTION (Exclude technical IDs if any)
            for key in ["description", "caption", "comment", "title"]:
                val = rel["properties"].get(key)
                if val and isinstance(val, str):
                    terms_to_translate.add(val)

    translated = await translate_terms(list(terms_to_translate), language, model)

    # Apply translations
    def get_translated(term):
        return translated.get(term, term)

    for node in nodes:
        if node and "labels" in node:
            if "original_labels" not in node:
                node["original_labels"] = list(node["labels"])
            node["labels"] = [get_translated(label) for label in node["labels"]]
        
        if node and "properties" in node:
            # Preserve original properties before translation
            if "original_properties" not in node["properties"]:
                node["properties"]["original_properties"] = node["properties"].copy()
            
            # Translate only display-friendly keys (EXCLUDE 'id' from translation)
            display_keys = ["name", "fileName", "label", "description", "title", "caption"]
            for key in display_keys:
                val = node["properties"].get(key)
                if val and isinstance(val, str):
                    node["properties"][key] = get_translated(val)

    for rel in relationships:
        if rel and "type" in rel:
            if "original_type" not in rel:
                rel["original_type"] = rel["type"]
            rel["type"] = get_translated(rel["type"])
            
        if rel and "properties" in rel:
            # Preserve original properties
            if "original_properties" not in rel["properties"]:
                rel["properties"]["original_properties"] = rel["properties"].copy()
            
            # Translate only display-friendly keys
            display_keys = ["description", "caption", "comment", "title"]
            for key in display_keys:
                val = rel["properties"].get(key)
                if val and isinstance(val, str):
                    rel["properties"][key] = get_translated(val)

    return nodes, relationships

async def translate_metadata(metadata, language, model):
    """
    Translate entity IDs and node details in the chat metadata.
    """
    if not language or language == "en":
        return metadata

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
            for key in ["id", "name", "description", "label", "caption", "title"]:
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

    translated = await translate_terms(list(terms_to_translate), language, model)

    # Apply translations back to metadata
    def get_translated(term):
        return translated.get(term, term)

    # Apply to entities
    if "entities" in metadata:
        for key in ["entityids", "relationshipids"]:
            if key in metadata["entities"]:
                metadata["entities"][key] = [get_translated(t) for t in metadata["entities"][key]]

    # Apply to nodedetails
    if "nodedetails" in metadata:
        for detail in metadata["nodedetails"].get("entitydetails", []):
            if isinstance(detail, dict):
                # Preserve original details
                if "original_details" not in detail:
                    detail["original_details"] = detail.copy()
                
                # NEVER translate 'id' in metadata details either
                for key in ["name", "description", "label", "caption", "title"]:
                    if key in detail and isinstance(detail[key], str):
                        detail[key] = get_translated(detail[key])
        
        for community in metadata["nodedetails"].get("communitydetails", []):
            if isinstance(community, dict) and "label" in community:
                if "original_label" not in community:
                    community["original_label"] = community["label"]
                community["label"] = get_translated(community["label"])
    
    # Apply to sources
    if "sources" in metadata:
        if "original_sources" not in metadata:
             metadata["original_sources"] = list(metadata["sources"])
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

Strict Output Format (JSON ONLY):
{{"original_term": "translated_term", ...}}

CRITICAL RULES:
1. Provide ONLY the JSON object.
2. DO NOT include any conversational filler, explanations, "Okay", "Here is", "Sure", or notes.
3. Every value in the JSON MUST be in {target_language}.
4. If you output ANY text outside the JSON, the system will fail.
"""

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
        
        # Validation and cleaning of values
        validated_translations = {}
        for term, translated in translations.items():
                # Check for conversational rubbish
                rubbish_indicators = [
                    "intended translation", "maybe", "wait", "user wrote", "medical term", 
                    "in tamil", "in hindi", "okay,", "let's", "i need to", "user wants", 
                    "translate", "translation", "sure,", "here is", "i think", "medical platform",
                    "the phrase", "means", "is a", "next part", "tackle this", "உருப்படி உள்ளது",
                    "அடுத்த பகுதி", "தொடர்புடையது", "குறிப்பிடப்பட்டுள்ளது"
                ]
                is_rubbish = any(indicator in translated.lower() for indicator in rubbish_indicators)
                
                # Check for unusually long translations: much longer than the term itself
                # means the model added explanation (long entity names are fine)
                if not is_rubbish and len(translated) > max(60, 3 * len(str(term))):
                    is_rubbish = True
                
                # Check for excessive English words in non-English translation
                if target_language.lower() not in ["english", "french", "german", "spanish"]:
                    # Common English stop words that shouldn't appear in e.g. Tamil translations
                    english_stop_words = re.findall(r'\b(the|is|at|which|on|for|of|to|and|a|an|it|with|for|as|by)\b', translated.lower())
                    if len(english_stop_words) > 1:
                        is_rubbish = True
                    
                    # Existing check for long English sequences
                    english_sequences = re.findall(r'[a-zA-Z]{3,}', translated)
                    if len(english_sequences) > 5:
                        is_rubbish = True
                
                if not is_rubbish:
                    validated_translations[term] = translated
                else:
                    logging.warning(f"RUBBISH DETECTED in LLM output: '{translated}' for term '{term}'. Falling back.")
        
        # Fallback for missing or rejected terms
        for term in terms:
            if term not in validated_translations:
                validated_translations[term] = term
        return validated_translations
    except Exception as e:
        logging.error(f"LOCALIZATION Error: LLM translation failed: {e}")
        return {term: term for term in terms}
