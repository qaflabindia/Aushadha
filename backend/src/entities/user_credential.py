from pydantic import BaseModel, Field, validator
from typing import Optional
from fastapi import Form, HTTPException
from src.shared.env_utils import get_value_from_env

class Neo4jCredentials(BaseModel):
    """
    Neo4j database credentials model with validation.
    Used as a dependency for FastAPI endpoints requiring database access.
    """
    uri: Optional[str] = Field(None, description="Neo4j database URI")
    userName: Optional[str] = Field(None, description="Neo4j username")
    password: Optional[str] = Field(None, description="Neo4j password")
    database: Optional[str] = Field(None, description="Neo4j database name")
    email: Optional[str] = Field(None, description="User email for logging")
    target_user_email: Optional[str] = Field(None, description="Email of the patient being impersonated by an Admin/Doctor/Staff")
    user_role: Optional[str] = Field(None, description="Role of the authenticated user")

    def validate_required(self) -> None:
        """Validate that required credentials are present"""
        if not self.uri or not self.userName or not self.password:
            raise HTTPException(
                status_code=400,
                detail="Missing required credentials: uri, userName, and password are required"
            )

    class Config:
        """Pydantic configuration"""
        str_strip_whitespace = True  # Automatically strip whitespace from strings

    @validator('uri', pre=True, always=True)
    def validate_uri(cls, v):
        """Validate and fix URI format"""
        if v:
            if isinstance(v, str):
                v = v.lower()
                if 'localhost' in v or '127.0.0.1' in v:
                    v = v.replace('localhost', 'neo4j').replace('127.0.0.1', 'neo4j')
                
                # Ensure protocol is present
                if not (v.startswith('bolt://') or 
                        v.startswith('neo4j://') or 
                        v.startswith('bolt+s://') or 
                        v.startswith('neo4j+s://')):
                    v = f"bolt://{v}"
        return v


async def get_neo4j_credentials(
    uri: Optional[str] = Form(None),
    userName: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    database: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    target_user_email: Optional[str] = Form(None),
    user_role: Optional[str] = Form(None)
) -> Neo4jCredentials:
    """
    FastAPI dependency function to extract and validate Neo4j credentials from form data.
    
    Args:
        uri: Neo4j database URI
        userName: Neo4j username
        password: Neo4j password  
        database: Neo4j database name (optional, defaults to neo4j)
        email: User email for logging purposes
    
    Returns:
        Neo4jCredentials: Validated credentials object
    
    Raises:
        HTTPException: If validation fails
    """
    if not uri:
        uri = get_value_from_env("NEO4J_URI")
    if not userName:
        userName = get_value_from_env("NEO4J_USERNAME")
    if not password:
        password = get_value_from_env("NEO4J_PASSWORD")
    if not database:
        database = get_value_from_env("NEO4J_DATABASE", "neo4j")

    return Neo4jCredentials(
        uri=uri,
        userName=userName,
        password=password,
        database=database,
        email=email,
        target_user_email=target_user_email,
        user_role=user_role
    )