from typing import List, Optional
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.models.enums import UserRole, UserStatus
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None)
) -> User:
    """Validate Bearer JWT token and return the associated active user."""
    raw_token = token
    if not raw_token and authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization.split(" ")[1]

    if not raw_token:
        raise AuthenticationError("Authorization token is missing. Please log in.")

    payload = decode_access_token(raw_token)
    if not payload:
        raise AuthenticationError("Invalid or expired access token.")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token payload missing subject identifier.")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise AuthenticationError("Malformed user identifier in token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError("User associated with this token does not exist.")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active (not terminated)."""
    if current_user.status == UserStatus.TERMINATED:
        raise ForbiddenError("User account has been terminated.")
    return current_user


class RoleChecker:
    """Role-Based Access Control (RBAC) dependency validator."""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in self.allowed_roles:
            role_names = ", ".join([r.value for r in self.allowed_roles])
            raise ForbiddenError(f"Access denied. Requires one of roles: [{role_names}]. Your role: {current_user.role.value}")
        return current_user


# Role shortcuts
require_admin = RoleChecker([UserRole.ADMIN])
require_manager_or_admin = RoleChecker([UserRole.ADMIN, UserRole.MANAGER])
require_any_user = get_current_active_user
