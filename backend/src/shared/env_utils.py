import os
import json
import logging
from typing import Any
from src.shared.secret_vault import get_secret

def convert_type(value: Any, data_type: Any):
    """Convert value to the specified data type."""
    try:
        if data_type in (int, "int"):
            return int(value)
        elif data_type in (float, "float"):
            return float(value)
        elif data_type in (bool, "bool"):
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                return value.strip().lower() in ["true", "1", "yes"]
            raise ValueError(f"Cannot convert {value!r} to bool")
        elif data_type in (list, dict, "list", "dict"):
            if isinstance(value, (list, dict)):
                return value
            return json.loads(value)
        elif data_type in (str, "str"):
            return str(value)
        else:
            return value
    except Exception as e:
        logging.error(f"Type conversion error for value {value} to {data_type}: {e}")
        return value

def get_value_from_env(key_name: str, default_value: Any = None, data_type: Any = str):
    """
    Retrieve a value from the secret vault or environment variables.
    """
    # First check the secret vault
    value = get_secret(key_name)
    
    # Then check environment variables
    if value is None:
        value = os.getenv(key_name, None)
        
    if value is not None and str(value).strip() != "":
        return convert_type(value, data_type)
    elif default_value is not None:
        return convert_type(default_value, data_type)
    else:
        # logging.debug(f"Environment variable or secret '{key_name}' not found and no default value provided.")
        return None
