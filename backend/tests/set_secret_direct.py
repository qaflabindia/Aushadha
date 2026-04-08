
import os
import sys

# Add backend to sys.path
backend_path = os.path.abspath(os.path.join(os.getcwd(), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

os.environ["VAULT_MASTER_PASSWORD"] = "YOUR_VAULT_PASSWORD"
os.environ["VAULT_FILE_PATH"] = os.path.join(backend_path, ".secrets.vault")

from src.shared.secret_vault import set_secret

def main():
    key = "OPENAI_API_KEY"
    value = "YOUR_OPENAI_API_KEY"
    print(f"Setting secret {key} in vault at {os.environ['VAULT_FILE_PATH']}...")
    set_secret(key, value)
    print("SUCCESS: Secret set in vault.")

if __name__ == "__main__":
    main()
