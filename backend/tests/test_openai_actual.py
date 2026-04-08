
import os
import sys
import logging

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.getcwd(), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Set environment variables from .env manually for this test if needed
# But get_value_from_env should handle it if we run from the right CWD
os.environ["VAULT_MASTER_PASSWORD"] = "Aushadha@Vault2026!"
os.environ["VAULT_FILE_PATH"] = os.path.abspath("backend/.secrets.vault")

from src.shared.env_utils import get_value_from_env
from openai import OpenAI

def test_openai_connectivity():
    logging.basicConfig(level=logging.INFO)
    
    # 1. Get the key
    api_key = get_value_from_env("OPENAI_API_KEY")
    
    if not api_key:
        print("FAILED: OPENAI_API_KEY not found in vault or environment.")
        return

    print(f"DEBUG: Found API Key (first 10 chars): {api_key[:10]}...")
    
    # 2. Try the call
    client = OpenAI(api_key=api_key)
    try:
        print("Attempting a simple chat completion call (gpt-4o-mini for speed/cost)...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Aushadha Connection Success'"}],
            max_tokens=10
        )
        result = response.choices[0].message.content.strip()
        print(f"RESULT: {result}")
        
        # 3. Check gpt-4.5 Specifically (if possible, though it might not be available or name might differ)
        # The user requested to check "Openai gpt 4.5"
        # In .env it's mapped to "gpt-4.5"
        print("Attempting a call with model 'gpt-4.5'...")
        response_45 = client.chat.completions.create(
            model="gpt-4.5",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        print(f"GPT-4.5 RESULT: {response_45.choices[0].message.content.strip()}")
        
    except Exception as e:
        print(f"FAILED: OpenAI API call failed: {e}")

if __name__ == "__main__":
    test_openai_connectivity()
