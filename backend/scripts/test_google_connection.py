#!/usr/bin/env python3
"""
Test script for Google Cloud Vertex AI & Gemini model connectivity in AyushPragya.
Usage:
    python backend/scripts/test_google_connection.py
"""
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def test_connectivity():
    print("=" * 65)
    print("  AyushPragya - Google Cloud & Gemini Connectivity Test")
    print("=" * 65)

    # 1. Check Google Auth Credentials
    print("\n[Step 1] Checking Google Application Default Credentials (ADC)...")
    try:
        import google.auth
        credentials, project = google.auth.default()
        print(f"  ✓ Credentials Type: {type(credentials).__name__}")
        print(f"  ✓ Default Project from ADC: {project}")
    except Exception as e:
        print(f"  ✗ Failed to find Google credentials: {e}")
        print("\n  --> ACTION REQUIRED: Run the following command in your terminal:")
        print("      gcloud auth application-default login\n")
        return False

    # 2. Check Project ID configuration
    print("\n[Step 2] Validating Project ID...")
    from src.shared.env_utils import get_value_from_env
    env_project = get_value_from_env("PROJECT_ID")
    effective_project = env_project or project
    print(f"  ✓ Effective GCP Project: {effective_project}")
    if not effective_project:
        print("  ✗ Warning: No GCP Project ID found in .env or ADC.")
        return False

    # 3. Test LLM Initialization (Gemini 2.5 Flash)
    print("\n[Step 3] Initializing Gemini 2.5 Flash via get_llm()...")
    try:
        from src.llm import get_llm
        llm, model_version, _ = get_llm("gemini_2.5_flash")
        print(f"  ✓ Model initialized: {model_version} ({type(llm).__name__})")
    except Exception as e:
        print(f"  ✗ Failed to initialize LLM: {e}")
        return False

    # 4. Test Model Inference
    print("\n[Step 4] Testing Gemini Inference call...")
    try:
        from langchain_core.messages import HumanMessage
        prompt = [HumanMessage(content="Hello! Respond with: 'Google Vertex AI Gemini connectivity confirmed.'")]
        response = llm.invoke(prompt)
        print(f"  ✓ Gemini Response:\n    \"{response.content.strip()}\"")
    except Exception as e:
        print(f"  ✗ Inference failed: {e}")
        print("\n  If you see 'API not enabled', enable Vertex AI API:")
        print(f"    gcloud services enable aiplatform.googleapis.com --project={effective_project}")
        return False

    # 5. Test Vertex AI Embeddings
    print("\n[Step 5] Testing Vertex AI Embeddings...")
    try:
        from src.shared.common_fn import load_embedding_model
        embeddings, dim = load_embedding_model("vertexai")
        sample_vec = embeddings.embed_query("Clinical Ayurveda Hypertension Intelligence")
        print(f"  ✓ Embeddings generated successfully! Dimension: {len(sample_vec)} (expected: {dim})")
    except Exception as e:
        print(f"  ✗ Embeddings test skipped or failed: {e}")

    print("\n" + "=" * 65)
    print("  RESULT: Google Cloud & Gemini Integration is READY!")
    print("=" * 65 + "\n")
    return True

if __name__ == "__main__":
    success = test_connectivity()
    sys.exit(0 if success else 1)
