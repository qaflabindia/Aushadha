
import os
import sys
from dotenv import load_dotenv

# DIAGNOSTIC SCRIPT

print(f"CWD: {os.getcwd()}")
print(f"File exists: {os.path.exists('.env')}")

# Load .env
load_dotenv(override=True)

# Check specifically for OPENAI_API_KEY
key = "OPENAI_API_KEY"
val = os.getenv(key)

print(f"Value for {key}: {val[:10] + '...' if val else 'None'}")

# Now check via the app's utility
backend_path = os.path.abspath(os.path.join(os.getcwd()))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.shared.env_utils import get_value_from_env
val_util = get_value_from_env(key)
print(f"Value via get_value_from_env: {val_util[:10] + '...' if val_util else 'None'}")
