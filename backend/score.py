# =============================================================================
# Aushadha — Application Composition Root
# =============================================================================
# This is the FastAPI entry point. It creates the app, applies middleware,
# and registers all router modules. No endpoint logic lives here.
#
# Entrypoint: score:app  (used by uvicorn/gunicorn, Dockerfile, docker-compose)
# =============================================================================

import os
from typing import List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi_health import health
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from Secweb.XContentTypeOptions import XContentTypeOptions
from Secweb.XFrameOptions import XFrame

load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Health check functions
# ---------------------------------------------------------------------------

def healthy_condition():
    return {"database": True}

def healthy():
    return True


# ---------------------------------------------------------------------------
# Custom GZip Middleware
# ---------------------------------------------------------------------------

class CustomGZipMiddleware:
    """Custom GZip middleware to compress responses for specific paths."""

    def __init__(self, app: ASGIApp, paths: List[str], minimum_size: int = 1000, compresslevel: int = 5):
        self.app = app
        self.paths = paths
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            if any(path.startswith(p) for p in self.paths):
                gzip_middleware = GZipMiddleware(
                    self.app,
                    minimum_size=self.minimum_size,
                    compresslevel=self.compresslevel
                )
                await gzip_middleware(scope, receive, send)
                return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# App creation & middleware
# ---------------------------------------------------------------------------

app = FastAPI()
app.add_middleware(XContentTypeOptions)
app.add_middleware(XFrame, Option={'X-Frame-Options': 'DENY'})
app.add_middleware(
    CustomGZipMiddleware,
    minimum_size=1000,
    compresslevel=5,
    paths=[
        "/sources_list",
        "/graph_query",
        "/chunk_entities",
        "/get_neighbours",
        "/get_unconnected_nodes_list",
        "/get_duplicate_nodes",
        "/schema_visualization"
    ]
)

# CORS: Restrict to explicit origins. Configure via ALLOWED_ORIGINS env var
_default_origins = "http://localhost:8080,http://localhost:5173,http://localhost:3000,http://127.0.0.1:8080,http://127.0.0.1:5173"
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", os.urandom(24).hex()))
app.add_api_route("/health", health([healthy_condition, healthy]))


# ---------------------------------------------------------------------------
# Router Registration
# ---------------------------------------------------------------------------

from src.routers.graph_router import router as graph_router
from src.routers.chat_router import router as chat_router
from src.routers.clinical_router import router as clinical_router
from src.routers.admin_router import router as admin_router
from src.routers.metrics_router import router as metrics_router
from src.routers.auth_router import router as auth_router
from src.routers.rbac_router import router as rbac_router

app.include_router(graph_router)
app.include_router(chat_router)
app.include_router(clinical_router)
app.include_router(admin_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(rbac_router)


if __name__ == "__main__":
    uvicorn.run(app)
