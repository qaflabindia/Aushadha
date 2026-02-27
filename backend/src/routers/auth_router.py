import logging
import os

from fastapi import APIRouter, Depends, Request

from src.api_response import create_api_response
from src.shared.google_auth import require_auth, create_local_token, AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/local_login")
async def local_login(request: Request):
    """
    Issue a local RS256-signed JWT.
    Accepts JSON body: {"email": "...", "password": "..."}
    For now, validates against LOCAL_AUTH_PASSWORD env var (simple shared secret).
    """
    try:
        data = await request.json()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        name = data.get("name", email.split("@")[0] if "@" in email else email)

        if not email or not password:
            return create_api_response("Failed", message="Email and password are required")

        expected_password = os.getenv("LOCAL_AUTH_PASSWORD", "aushadha2026")
        if password != expected_password:
            return create_api_response("Failed", message="Invalid credentials")

        token = create_local_token(email=email, name=name)
        return create_api_response("Success", data={
            "token": token,
            "email": email,
            "name": name,
            "auth_method": "local"
        }, message="Login successful")
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.post("/google_verify")
async def google_verify(request: Request):
    """
    Verify a Google ID token and return user info + local JWT for session continuity.
    Accepts JSON body: {"id_token": "..."}
    """
    try:
        data = await request.json()
        id_token = data.get("id_token", "").strip()
        if not id_token:
            return create_api_response("Failed", message="id_token is required")

        from src.shared.google_auth import _verify_google_token
        user = _verify_google_token(id_token)
        if not user:
            return create_api_response("Failed", message="Invalid Google token")

        local_token = create_local_token(email=user.email, name=user.name)
        return create_api_response("Success", data={
            "token": local_token,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "auth_method": "google"
        }, message="Google authentication successful")
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.get("/me")
async def auth_me(user: AuthenticatedUser = Depends(require_auth)):
    """Return the currently authenticated user's info."""
    return create_api_response("Success", data={
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "auth_method": user.auth_method,
    })
