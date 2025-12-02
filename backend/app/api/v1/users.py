"""User management API endpoints (admin only)."""

import logging

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user, require_admin
from app.config import get_settings
from app.db import get_db
from app.models.api_key import APIKey
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class CreateAPIKeyRequest(BaseModel):
    """Request body for creating an API key."""

    name: str


class InviteUserRequest(BaseModel):
    """Request body for inviting a new user."""

    email: EmailStr
    role: str = "viewer"


# ============================================
# Static routes MUST come before parameterized routes
# ============================================


@router.get("/me")
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get current user info including database role."""
    return {
        "cognito_sub": current_user.cognito_sub,
        "email": current_user.email,
        "role": current_user.role,
        "id": current_user.db_user.id if current_user.db_user else None,
    }


@router.post("/invite")
def invite_user(
    request: InviteUserRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Invite a new user via Cognito. Sends email with temporary password."""
    if request.role not in ("viewer", "editor", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    if not settings.cognito_user_pool_id:
        raise HTTPException(status_code=500, detail="Cognito not configured on server")

    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    try:
        cognito = boto3.client("cognito-idp", region_name=settings.aws_region)
        response = cognito.admin_create_user(
            UserPoolId=settings.cognito_user_pool_id,
            Username=request.email,
            UserAttributes=[
                {"Name": "email", "Value": request.email},
                {"Name": "email_verified", "Value": "true"},
            ],
            DesiredDeliveryMediums=["EMAIL"],
        )

        cognito_sub = None
        for attr in response["User"]["Attributes"]:
            if attr["Name"] == "sub":
                cognito_sub = attr["Value"]
                break

        if cognito_sub:
            new_user = User(cognito_sub=cognito_sub, email=request.email, role=request.role)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return {
                "message": f"Invitation sent to {request.email}",
                "user_id": new_user.id,
                "cognito_sub": cognito_sub,
            }
        else:
            return {
                "message": f"Invitation sent to {request.email}",
                "note": "User will be created in database on first login",
            }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        logger.error(f"Cognito error: {error_code} - {error_msg}")
        if error_code == "UsernameExistsException":
            raise HTTPException(
                status_code=400,
                detail="A user with this email already exists in Cognito",
            ) from None
        elif error_code == "InvalidParameterException":
            raise HTTPException(status_code=400, detail=error_msg) from None
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to create user: {error_msg}"
            ) from None


@router.get("/api-keys")
def list_api_keys(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """List all API keys. Requires admin role."""
    keys = db.query(APIKey).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "created_by_id": k.created_by_id,
            "created_by_email": k.created_by.email if k.created_by else None,
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in keys
    ]


@router.post("/api-keys")
def create_api_key(
    request: CreateAPIKeyRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Create a new API key. Returns the key only once. Requires admin role."""
    if not current_user.db_user:
        raise HTTPException(status_code=400, detail="User not found in database")

    # Generate new key
    raw_key = APIKey.generate_key()
    key_hash = APIKey.hash_key(raw_key)
    key_prefix = raw_key[:8]

    api_key = APIKey(
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        created_by_id=current_user.db_user.id,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,  # Only returned once!
        "key_prefix": key_prefix,
        "message": "Save this key now - it won't be shown again",
    }


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Revoke (deactivate) an API key. Requires admin role."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()
    return {"message": f"API key {key_id} revoked"}


# ============================================
# User list and parameterized routes
# ============================================


@router.get("")
def list_users(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """List all users. Requires admin role."""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "cognito_sub": u.cognito_sub,
            "email": u.email,
            "role": u.role,
        }
        for u in users
    ]


@router.put("/{user_id}/role")
def update_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Update a user's role. Requires admin role."""
    if role not in ("viewer", "editor", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()
    return {"message": f"User {user_id} role updated to {role}"}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Delete a user. Requires admin role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Don't allow deleting yourself
    if current_user.db_user and current_user.db_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Delete associated API keys first
    db.query(APIKey).filter(APIKey.created_by_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": f"User {user_id} deleted"}
