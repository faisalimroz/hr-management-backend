from datetime import timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.audit import log_audit
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.models.department import Department
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Validate credentials and return User if valid."""
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        raise AuthenticationError("Incorrect email or password.")
    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password.")
    if user.status == UserStatus.TERMINATED:
        raise AuthenticationError("User account has been terminated.")
    return user


def login_user(db: Session, login_data: LoginRequest, ip_address: Optional[str] = None) -> Token:
    """Process user login and issue JWT access token."""
    user = authenticate_user(db, login_data.email, login_data.password)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "name": user.full_name,
    }
    access_token = create_access_token(token_payload, expires_delta=access_token_expires)

    log_audit(
        db,
        action="USER_LOGIN",
        user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details=f"User {user.email} logged in successfully",
        ip_address=ip_address,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


def register_user(
    db: Session,
    user_in: UserCreate,
    admin_user: User,
    ip_address: Optional[str] = None
) -> UserResponse:
    """Admin-only onboarding: Register a new employee/user in the system."""
    existing_user = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing_user:
        raise ConflictError(f"A user with email '{user_in.email}' already exists.")

    # Validate department if provided
    if user_in.department_id:
        dept = db.query(Department).filter(Department.id == user_in.department_id).first()
        if not dept:
            raise NotFoundError(f"Department with ID {user_in.department_id} not found.")

    # Validate manager if provided
    if user_in.manager_id:
        mgr = db.query(User).filter(User.id == user_in.manager_id).first()
        if not mgr:
            raise NotFoundError(f"Manager with ID {user_in.manager_id} not found.")

    new_user = User(
        first_name=user_in.first_name.strip(),
        last_name=user_in.last_name.strip(),
        email=user_in.email.lower().strip(),
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        status=user_in.status,
        department_id=user_in.department_id,
        manager_id=user_in.manager_id,
        phone_number=user_in.phone_number,
        designation=user_in.designation,
        office_location=user_in.office_location,
        date_of_joining=user_in.date_of_joining,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit(
        db,
        action="USER_ONBOARDED",
        user_id=admin_user.id,
        resource_type="user",
        resource_id=str(new_user.id),
        details=f"Admin {admin_user.email} onboarded new user {new_user.email} (Role: {new_user.role.value})",
        ip_address=ip_address,
    )

    return build_user_response(new_user)


def build_user_response(user: User) -> UserResponse:
    """Format SQLAlchemy User model into UserResponse with related names."""
    return UserResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        designation=user.designation,
        office_location=user.office_location,
        role=user.role,
        status=user.status,
        department_id=user.department_id,
        department_name=user.department.name if user.department else None,
        manager_id=user.manager_id,
        manager_name=user.manager.full_name if user.manager else None,
        date_of_joining=user.date_of_joining,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
