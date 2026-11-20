"""Require a signed-in user on every backend route (public deployments).

Off by default, so local development is unchanged. Set REQUIRE_AUTH_ALL=true to turn it on.

When on, every request must carry a valid Google ID token or local JWT, in the
Authorization header, the X-Auth-Token header, or a `token` query parameter (the last is
for EventSource streams, which cannot set headers). The only exceptions are CORS
preflight, the health check, the two login routes and the pre-login UI translations.

The verified user is stored on the request scope (request.state.auth_user) so that
routes can trust it instead of the email and role fields the browser sends.
"""
import json
import logging
import os
import time
from urllib.parse import parse_qs

from src.shared.google_auth import _verify_token

logger = logging.getLogger(__name__)

REQUIRE_AUTH_ALL = os.getenv("REQUIRE_AUTH_ALL", "false").strip().lower() in ("1", "true", "yes")

# Reachable without signing in
PUBLIC_PATHS = {
    "/health",
    "/auth/local_login",
    "/auth/google_verify",
    "/translate/ui/strings",
    "/translate/ui/batch",  # serves cached translations only to anonymous callers
}


_CACHE_SECONDS = 300
_CACHE_MAX = 2000
_verified: dict[str, tuple[float, object]] = {}


def _verify_cached(token: str):
    """Verify a token, remembering successes for a few minutes.

    Each verification tries Google first, which costs a network round trip even for
    local tokens; the gate runs on every request, so cache the result.
    """
    now = time.monotonic()
    hit = _verified.get(token)
    if hit and now - hit[0] < _CACHE_SECONDS:
        return hit[1]
    user = _verify_token(token)
    if user is not None:
        if len(_verified) >= _CACHE_MAX:
            _verified.clear()
        _verified[token] = (now, user)
    return user


def _token_from_scope(scope) -> str | None:
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    if headers.get("x-auth-token"):
        return headers["x-auth-token"].strip()
    query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
    if query.get("token"):
        return query["token"][0].strip() or None
    return None


class RequireAuthMiddleware:
    """Pure ASGI middleware, so streaming responses (SSE) pass through untouched."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if not REQUIRE_AUTH_ALL or scope.get("type") != "http" or scope.get("method") == "OPTIONS":
            return await self.app(scope, receive, send)

        token = _token_from_scope(scope)
        user = _verify_cached(token) if token else None
        scope.setdefault("state", {})["auth_user"] = user

        if user is None and scope.get("path", "") not in PUBLIC_PATHS:
            body = json.dumps({"detail": "Authentication required"}).encode()
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")],
            })
            await send({"type": "http.response.body", "body": body})
            return

        return await self.app(scope, receive, send)


def authenticated_identity(request):
    """Return (email, role) of the signed-in user when the gate is on, else (None, None).

    The role is read from the user table, never from the request.
    """
    if not REQUIRE_AUTH_ALL:
        return None, None
    user = getattr(request.state, "auth_user", None) if request is not None else None
    if user is None:
        return None, None
    from src.database import SessionLocal
    from src.models import User

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.email == user.email).first()
        role = db_user.role.name if db_user and db_user.role else ""
    finally:
        db.close()
    return user.email, role
