import os
import sys

# Add the /code directory to sys.path to import src modules
sys.path.append('/code')

from src.shared.secret_vault import set_secret
from src.shared.env_utils import get_value_from_env

def seed_secrets():
    secrets_to_seed = [
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_DATABASE",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "SARVAM_API_KEY",
        "OPENAI_API_KEY"
    ]
    
    for key in secrets_to_seed:
        # Get from env (which might be from .env if load_dotenv was called)
        value = os.getenv(key)
        if value:
            print(f"Seeding secret: {key}")
            set_secret(key, value)
        else:
            print(f"Warning: {key} not found in environment.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    seed_secrets()
    print("Seeding complete.")
