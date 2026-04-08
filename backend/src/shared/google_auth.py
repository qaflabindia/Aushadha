# =============================================================================
# Aushadha — Authentication Module
# =============================================================================
# Dual-mode authentication:
#   1. Google Sign-In  — Verifies Google ID tokens via Google's public keys
#   2. Local Auth      — RSA-256 (RS256) signed JWTs for offline / internal use
#
# Usage in endpoints:
#   from src.shared.google_auth import require_auth, optional_auth
#   @app.get("/protected", dependencies=[Depends(require_auth)])
#   async def protected_endpoint(user=Depends(require_auth)): ...
# =============================================================================

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID",
    "256164019269-o0174fcoksuls9hf9b9nkto42fc1c649.apps.googleusercontent.com",
)
AUTH_MODE = os.getenv("AUTH_MODE", "all")  # "google", "local", "all", "none"
# Renamed to clarify intent and added production safeguards
APP_ENV = os.getenv("APP_ENV", "development").lower()
STAGING_SKIP_AUTH = os.getenv("BACKEND_STAGING_SKIP_AUTH", "false").strip().lower() == "true"
SKIP_AUTH = STAGING_SKIP_AUTH and APP_ENV != "production"

# Logger must be initialized before any module-level code that uses it
logger = logging.getLogger(__name__)

if STAGING_SKIP_AUTH and APP_ENV == "production":
    logger.error("CRITICAL: BACKEND_STAGING_SKIP_AUTH is enabled in a production environment. Bypassing this flag for safety.")

# Local RSA-256 key paths (auto-generated if missing)
LOCAL_RSA_PRIVATE_KEY_PATH = Path(os.getenv("RSA_PRIVATE_KEY_PATH", "/code/.auth_rsa_private.pem"))
LOCAL_RSA_PUBLIC_KEY_PATH = Path(os.getenv("RSA_PUBLIC_KEY_PATH", "/code/.auth_rsa_public.pem"))

# Local token settings
LOCAL_TOKEN_EXPIRY_HOURS = int(os.getenv("LOCAL_TOKEN_EXPIRY_HOURS", "8"))  # default: 8 hours
LOCAL_TOKEN_ISSUER = "aushadha-local"

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# User model returned by auth dependencies
# ---------------------------------------------------------------------------
class AuthenticatedUser(BaseModel):
    email: str
    name: str = ""
    picture: str = ""
    auth_method: str = "unknown"  # "google" or "local"
    role: str = ""


# ---------------------------------------------------------------------------
# Google Token Verification
# ---------------------------------------------------------------------------
def _verify_google_token(token: str) -> Optional[AuthenticatedUser]:
    """Verify a Google ID token and return user info."""
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        # Verify issuer
        if idinfo["iss"] not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning("Google token has invalid issuer: %s", idinfo["iss"])
            return None

        return AuthenticatedUser(
            email=idinfo.get("email", ""),
            name=idinfo.get("name", ""),
            picture=idinfo.get("picture", ""),
            auth_method="google",
        )
    except Exception as e:
        logger.warning("Google token verification failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Local RSA-256 JWT — Key Management
# ---------------------------------------------------------------------------
def _ensure_rsa_keys() -> tuple:
    """Generate RSA key pair if not present, return (private_key, public_key)."""
    if LOCAL_RSA_PRIVATE_KEY_PATH.exists() and LOCAL_RSA_PUBLIC_KEY_PATH.exists():
        private_key = serialization.load_pem_private_key(
            LOCAL_RSA_PRIVATE_KEY_PATH.read_bytes(), password=None, backend=default_backend()
        )
        public_key = serialization.load_pem_public_key(
            LOCAL_RSA_PUBLIC_KEY_PATH.read_bytes(), backend=default_backend()
        )
        return private_key, public_key

    logger.info("Generating new RSA-256 key pair for local authentication...")
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()

    # Save keys
    LOCAL_RSA_PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_RSA_PRIVATE_KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    LOCAL_RSA_PUBLIC_KEY_PATH.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    logger.info("RSA key pair generated and saved.")
    return private_key, public_key


def create_local_token(email: str, name: str = "") -> str:
    """Create an RS256-signed JWT for local authentication."""
    private_key, _ = _ensure_rsa_keys()

    payload = {
        "sub": email,
        "name": name,
        "email": email,
        "iss": LOCAL_TOKEN_ISSUER,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=LOCAL_TOKEN_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token


def _verify_local_token(token: str) -> Optional[AuthenticatedUser]:
    """Verify a locally issued RS256 JWT."""
    try:
        _, public_key = _ensure_rsa_keys()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=LOCAL_TOKEN_ISSUER,
        )
        return AuthenticatedUser(
            email=payload.get("email", payload.get("sub", "")),
            name=payload.get("name", ""),
            picture="",
            auth_method="local",
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Local token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Local token verification failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Unified Token Verification
# ---------------------------------------------------------------------------
def _verify_token(token: str) -> Optional[AuthenticatedUser]:
    """Try all enabled auth methods to verify the token."""
    if AUTH_MODE in ("google", "all"):
        user = _verify_google_token(token)
        if user:
            return user

    if AUTH_MODE in ("local", "all"):
        user = _verify_local_token(token)
        if user:
            return user

    return None


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------
async def require_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    Dependency that REQUIRES authentication.
    Returns AuthenticatedUser or raises 401.
    Skipped entirely when SKIP_AUTH is True (dev mode).
    """
    # Dev mode — skip auth
    if SKIP_AUTH:
        return AuthenticatedUser(
            email="dev@local",
            name="Dev User",
            auth_method="skip",
        )

    # Check Authorization header
    if credentials and credentials.credentials:
        user = _verify_token(credentials.credentials)
        if user:
            return user

    # Check X-Auth-Token header (alternative for non-Bearer flows)
    alt_token = request.headers.get("X-Auth-Token")
    if alt_token:
        user = _verify_token(alt_token)
        if user:
            return user

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide a valid Google ID token or local JWT in the Authorization header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthenticatedUser]:
    """
    Dependency that OPTIONALLY authenticates.
    Returns AuthenticatedUser if token is valid, None otherwise.
    Never raises 401.
    """
    if SKIP_AUTH:
        return AuthenticatedUser(
            email="dev@local",
            name="Dev User",
            auth_method="skip",
        )

    if credentials and credentials.credentials:
        user = _verify_token(credentials.credentials)
        if user:
            return user

    alt_token = request.headers.get("X-Auth-Token")
    if alt_token:
        return _verify_token(alt_token)

    return None
