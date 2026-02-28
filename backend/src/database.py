import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.shared.env_utils import get_value_from_env

POSTGRES_USER = get_value_from_env("POSTGRES_USER", "aushadha_user")
POSTGRES_PASSWORD = get_value_from_env("POSTGRES_PASSWORD", "aushadha_pass")
POSTGRES_HOST = get_value_from_env("POSTGRES_HOST", "postgres")
POSTGRES_PORT = get_value_from_env("POSTGRES_PORT", "5432")
POSTGRES_DB = get_value_from_env("POSTGRES_DB", "aushadha")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
