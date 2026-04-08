import os
from src.shared.env_utils import get_value_from_env

GCS_FILE_CACHE = get_value_from_env("GCS_FILE_CACHE", "False", "bool")
BUCKET_UPLOAD_FILE = get_value_from_env('BUCKET_UPLOAD_FILE', default_value=None, data_type=str)
BUCKET_FAILED_FILE = get_value_from_env('BUCKET_FAILED_FILE', default_value=None, data_type=str)
PROJECT_ID = get_value_from_env('PROJECT_ID', default_value=None, data_type=str)
