
import sys
import os
from pathlib import Path

# Add backend/src/shared to sys.path
backend_path = "/Users/lakshminarasimhan.santhanamgigkri.com/KG/backend"
sys.path.append(os.path.join(backend_path, "src"))

import shared.secret_vault as vault

# Override paths to local ones
vault.VAULT_KEY_PATH = Path(os.path.join(backend_path, ".vault.key"))
vault.VAULT_FILE_PATH = Path(os.path.join(backend_path, ".secrets.json.enc"))

# Configuration for Local LLM
# We use 'local-llm-proxy' because the backend is running in Docker and needs to reach the proxy container
config_name = "LLM_MODEL_CONFIG_LOCAL_LLAMA"
config_value = "mistral-7b,http://local-llm-proxy:8090/v1,no-key"

try:
    vault.set_secret(config_name, config_value)
    print(f"Successfully updated '{config_name}' in the vault.")
    print(f"New Value: {config_value}")
except Exception as e:
    print(f"Error: {e}")
