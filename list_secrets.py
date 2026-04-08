
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

try:
    keys = vault.list_secret_keys()
    if not keys:
        print("No secrets found in the vault.")
    else:
        print("Vault Entries:")
        for key in keys:
            val = vault.get_secret(key)
            print(f"- {key}: {val}")
except Exception as e:
    print(f"Error: {e}")
