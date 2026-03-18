import logging
import os

from fastapi import APIRouter, Depends, Request

from src.api_response import create_api_response
from src.database import get_db
from sqlalchemy.orm import Session
from src.models import User
from src.shared.google_auth import require_auth, create_local_token, AuthenticatedUser
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# pwd_context removed as we use bcrypt directly

import bcrypt

def verify_password(plain_password, hashed_password):
    try:
        if not hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logging.error(f"Password verification error: {e}")
        return False

@router.post("/local_login")
async def local_login(request: Request, db: Session = Depends(get_db)):
    """
    Issue a local RS256-signed JWT.
    Accepts JSON body: {"username_or_email": "...", "password": "..."}
    Validates hashed password from the database.
    """
    try:
        data = await request.json()
        username_or_email = data.get("email", data.get("username_or_email", "")).strip()
        password = data.get("password", "").strip()
        name = data.get("name", username_or_email.split("@")[0] if "@" in username_or_email else username_or_email)

        if not username_or_email or not password:
            logger.warning("Login failed: Missing username/email or password")
            return create_api_response("Failed", message="Username/Email and password are required")

        logger.info(f"Login attempt for: {username_or_email}")
        db_user = db.query(User).filter(User.email == username_or_email).first()
        
        if not db_user:
            logger.warning(f"Login failed: User not found: {username_or_email}")
            return create_api_response("Failed", message="Invalid credentials")

        if not db_user.hashed_password:
            logger.warning(f"Login failed: User {username_or_email} has no local password set")
            return create_api_response("Failed", message="Invalid credentials or user not configured for local login")
        
        if not verify_password(password, db_user.hashed_password):
            logger.warning(f"Login failed: Incorrect password for {username_or_email}")
            return create_api_response("Failed", message="Invalid credentials")

        logger.info(f"Login successful for: {username_or_email}")

        role = db_user.role.name if db_user and db_user.role else ""

        token = create_local_token(email=username_or_email, name=name)
        return create_api_response("Success", data={
            "token": token,
            "email": username_or_email,
            "name": name,
            "auth_method": "local",
            "role": role
        }, message="Login successful")
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.post("/google_verify")
async def google_verify(request: Request, db: Session = Depends(get_db)):
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

        db_user = db.query(User).filter(User.email == user.email).first()
        if not db_user:
            # Auto-provision first-time Google users
            from src.models import Role
            default_role = db.query(Role).filter(Role.name == "Patient").first()
            if not default_role:
                # Create role if missing (safeguard)
                default_role = Role(name="Patient")
                db.add(default_role)
                db.flush()
            
            db_user = User(
                email=user.email,
                role_id=default_role.id,
                # hashed_password is None for Google users
            )
            db.add(db_user)
            try:
                db.commit()
                db.refresh(db_user)
                logger.info(f"Auto-provisioned new user: {user.email}")
            except Exception as commit_error:
                db.rollback()
                return create_api_response("Failed", error=f"Auto-provisioning failed: {str(commit_error)}")
        
        role = db_user.role.name if db_user and db_user.role else "Patient"

        local_token = create_local_token(email=user.email, name=user.name)
        return create_api_response("Success", data={
            "token": local_token,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "auth_method": "google",
            "role": role
        }, message="Google authentication successful")
    except Exception as e:
        return create_api_response("Failed", error=str(e))


@router.get("/me")
async def auth_me(user: AuthenticatedUser = Depends(require_auth), db: Session = Depends(get_db)):
    """Return the currently authenticated user's info."""
    db_user = db.query(User).filter(User.email == user.email).first()
    role = db_user.role.name if db_user and db_user.role else ""
    return create_api_response("Success", data={
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "auth_method": user.auth_method,
        "role": role,
    })
