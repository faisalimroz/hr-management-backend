from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import login_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication & Onboarding"])


@router.post(
    "/login",
    response_model=Token,
    summary="User Login",
    description="Authenticate with email and password to receive a JWT Bearer access token."
)
def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    return login_user(db, login_data, ip_address=client_ip)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard New Employee (Admin Only)",
    description="Create a new employee profile. Requires Admin/HR privileges."
)
def register(
    user_in: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    return register_user(db, user_in, admin_user=admin_user, ip_address=client_ip)
