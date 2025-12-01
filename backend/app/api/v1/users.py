"""User management API endpoints (admin only)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models.user import User

router = APIRouter()


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
