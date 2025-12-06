"""Authentication and authorization module using AWS Cognito."""

import time
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.api_key import APIKey
from app.models.user import User

security = HTTPBearer(auto_error=False)
settings = get_settings()


def verify_api_key(api_key: str | None) -> bool:
    """Verify API key for CLI/automation access."""
    if not settings.api_key:
        return False
    return api_key == settings.api_key


@lru_cache(maxsize=1)
def get_cognito_jwks() -> dict:
    """Fetch and cache Cognito JWKS (JSON Web Key Set)."""
    if not settings.cognito_user_pool_id:
        return {}

    region = settings.cognito_user_pool_id.split("_")[0]
    jwks_url = (
        f"https://cognito-idp.{region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )

    response = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.json()


def get_signing_key(token: str) -> dict | None:
    """Get the signing key for a JWT token from Cognito JWKS."""
    jwks = get_cognito_jwks()
    if not jwks:
        return None

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def verify_cognito_token(token: str) -> dict | None:
    """Verify a Cognito JWT token and return claims."""
    import logging

    logger = logging.getLogger(__name__)

    if not settings.cognito_user_pool_id:
        logger.warning("Auth: No cognito_user_pool_id configured")
        return None

    try:
        signing_key = get_signing_key(token)
        if not signing_key:
            logger.warning("Auth: Could not get signing key for token")
            return None

        region = settings.cognito_user_pool_id.split("_")[0]
        issuer = f"https://cognito-idp.{region}.amazonaws.com/{settings.cognito_user_pool_id}"

        logger.info(
            f"Auth: Decoding token with issuer={issuer}, client_id={settings.cognito_app_client_id}"
        )

        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=settings.cognito_app_client_id,
            issuer=issuer,
            options={"verify_at_hash": False},
        )

        # Check token expiration
        if claims.get("exp", 0) < time.time():
            logger.warning(
                f"Auth: Token expired at {claims.get('exp')}, current time {time.time()}"
            )
            return None

        return claims
    except JWTError as e:
        logger.error(f"Auth: JWT verification error: {e}")
        return None


class CurrentUser:
    """Represents the current authenticated user."""

    def __init__(
        self,
        cognito_sub: str,
        email: str | None,
        role: str,
        db_user: User | None = None,
    ):
        self.cognito_sub = cognito_sub
        self.email = email
        self.role = role
        self.db_user = db_user

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_editor(self) -> bool:
        return self.role in ("admin", "editor")

    @property
    def is_viewer(self) -> bool:
        return self.role in ("admin", "editor", "viewer")


def verify_database_api_key(api_key: str, db: Session) -> APIKey | None:
    """Verify API key against database-stored keys (SHA-256 hashed)."""
    if not api_key:
        return None
    key_hash = APIKey.hash_key(api_key)
    db_key = (
        db.query(APIKey)
        .filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,  # noqa: E712
        )
        .first()
    )
    if db_key:
        # Update last_used_at timestamp
        from datetime import UTC, datetime

        db_key.last_used_at = datetime.now(UTC)
        db.commit()
    return db_key


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    x_api_key: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> CurrentUser | None:
    """Get current user from JWT token or API key (returns None if not authenticated)."""
    import logging

    logger = logging.getLogger(__name__)

    # Check static API key first (for backward compatibility)
    if verify_api_key(x_api_key):
        logger.info("Auth: Static API key authentication successful")
        return CurrentUser(
            cognito_sub="api-key-user",
            email="api@localhost",
            role="admin",
            db_user=None,
        )

    # Check database API keys (production keys with hashing)
    if x_api_key:
        db_api_key = verify_database_api_key(x_api_key, db)
        if db_api_key:
            logger.info(
                f"Auth: Database API key authentication successful (key: {db_api_key.key_prefix}...)"
            )
            # Get the user who created this key to inherit their role
            creator = db_api_key.created_by
            return CurrentUser(
                cognito_sub=f"api-key-{db_api_key.id}",
                email=creator.email if creator else "api@localhost",
                role=creator.role if creator else "admin",
                db_user=creator,
            )

    if credentials is None:
        logger.warning("Auth: No credentials provided")
        return None

    token = credentials.credentials
    logger.info(f"Auth: Verifying token (length={len(token) if token else 0})")
    claims = verify_cognito_token(token)

    if claims is None:
        logger.warning("Auth: Token verification failed")
        return None

    logger.info(f"Auth: Token verified, sub={claims.get('sub')}")

    cognito_sub = claims.get("sub")
    email = claims.get("email")

    # Look up user in database to get role
    db_user = db.query(User).filter(User.cognito_sub == cognito_sub).first()

    if db_user:
        role = db_user.role
    else:
        # New user - create with default viewer role
        db_user = User(cognito_sub=cognito_sub, email=email, role="viewer")
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        role = "viewer"

    return CurrentUser(
        cognito_sub=cognito_sub,
        email=email,
        role=role,
        db_user=db_user,
    )


async def get_current_user(
    user: Annotated[CurrentUser | None, Depends(get_current_user_optional)],
) -> CurrentUser:
    """Get current user (requires authentication)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_viewer(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Require viewer role or higher."""
    if not user.is_viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer access required",
        )
    return user


async def require_editor(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Require editor role or higher."""
    if not user.is_editor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor access required",
        )
    return user


async def require_admin(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Require admin role."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
