
import os
import sys
import re
from unittest.mock import MagicMock, patch

# STANDALONE TEST OF THE LOGIC ADDED TO llm.py

def get_value_from_env(key, default=None):
    # Mocked version of get_value_from_env
    env = {
        "LLM_MODEL_CONFIG_OPENAI_GPT_4_5": "gpt-4.5, OPENAI_API_KEY",
        "OPENAI_API_KEY": "actual-secret-key",
        "LLM_MODEL_CONFIG_GROQ_TEST": "llama-3, https://api.groq.com, GROQ_API_KEY",
        "GROQ_API_KEY": "groq-secret-key"
    }
    return env.get(key, default)

def test_logic():
    print("Verifying get_llm logic...")
    
    # Test Case 1: OpenAI with placeholder
    env_value = get_value_from_env("LLM_MODEL_CONFIG_OPENAI_GPT_4_5")
    parts = [get_value_from_env(p.strip()) or p.strip() for p in env_value.split(",")]
    model_name, api_key = parts[0], parts[1]
    
    print(f"OpenAI - Model: {model_name}, Key: {api_key}")
    assert model_name == "gpt-4.5"
    assert api_key == "actual-secret-key"
    
    # Test Case 2: Groq with placeholder
    env_value = get_value_from_env("LLM_MODEL_CONFIG_GROQ_TEST")
    parts = [get_value_from_env(p.strip()) or p.strip() for p in env_value.split(",")]
    model_name, base_url, api_key = parts[0], parts[1], parts[2]
    
    print(f"Groq - Model: {model_name}, URL: {base_url}, Key: {api_key}")
    assert model_name == "llama-3"
    assert base_url == "https://api.groq.com"
    assert api_key == "groq-secret-key"

    print("SUCCESS: Logic verified.")

if __name__ == "__main__":
    test_logic()
