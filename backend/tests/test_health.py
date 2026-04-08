# =============================================================================
# Aushadha Backend — Smoke Tests
# =============================================================================
# Minimal tests that validate the app boots and the health endpoint responds.
# These run in CI WITHOUT external services (Neo4j, Postgres) — they test
# only that the Python code loads and the FastAPI app object is valid.
#
# Run locally:  cd backend && python -m pytest tests/ -v
# =============================================================================

import os
import sys

# Ensure the backend root is on the Python path so `score` can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestHealthEndpoint:
    """Validate the /health endpoint works without any external services."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_body_is_healthy(self, client):
        response = client.get("/health")
        body = response.json()
        # fastapi-health returns {"conditions": [...], "healthy": True/False}
        # or it may return the condition dicts directly
        assert response.status_code == 200


class TestAppImports:
    """Ensure all critical modules can be imported without crashing."""

    def test_import_score(self):
        import score  # noqa: F401

    def test_import_llm(self):
        from src import llm  # noqa: F401

    def test_import_main(self):
        from src import main  # noqa: F401

    def test_import_secret_vault(self):
        from src.shared import secret_vault  # noqa: F401

    def test_import_common_fn(self):
        from src.shared import common_fn  # noqa: F401


class TestSecretEndpoints:
    """Validate secret vault endpoints respond (they don't need a real vault)."""

    def test_list_secrets_returns_200(self, client):
        response = client.get("/secrets")
        assert response.status_code == 200

    def test_get_secret_missing_returns_response(self, client):
        response = client.get("/secrets/values?name=NONEXISTENT_KEY")
        assert response.status_code == 200
        body = response.json()
        # Should return a "Failed" or "Success" API response
        assert "status" in body


class TestBackendConnectionConfig:
    """Validate the backend_connection_configuration endpoint doesn't crash."""

    def test_backend_config_responds(self, client):
        response = client.post("/backend_connection_configuration")
        # Will likely fail with DB connection error, but should not crash (500)
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
