# =============================================================================
# Aushadha Backend — Pytest Configuration & Fixtures
# =============================================================================
# Shared fixtures for all tests. The TestClient fixture allows testing
# FastAPI endpoints without starting a real server.
# =============================================================================

import os
import sys

import pytest

# Ensure backend root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set dummy env vars BEFORE importing score (which calls load_dotenv)
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "testdb")
os.environ.setdefault("POSTGRES_USER", "testuser")
os.environ.setdefault("POSTGRES_PASSWORD", "testpass")


@pytest.fixture(scope="session")
def client():
    """
    Create a FastAPI TestClient for the application.
    
    Scope is 'session' to avoid re-importing the app for every test,
    which is expensive due to model downloads and heavy imports.
    """
    from httpx import ASGITransport, AsyncClient
    from starlette.testclient import TestClient

    from score import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
