from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_any_user, require_admin
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserUpdate, UserProfileUpdate, UserResponse
from app.services.auth_service import build_user_response
from app.services.user_service import (
    get_user_by_id,
    list_users,
    update_own_profile,
    update_user_by_admin,
    offboard_user_by_admin,
)

router = APIRouter(prefix="/users", tags=["Users & Employee Management"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Logged-in User Profile",
    description="Retrieve the profile details of the currently authenticated user."
)
def get_my_profile(
    current_user: User = Depends(require_any_user),
):
    return build_user_response(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update Own Profile",
    description="Update personal details (names, contact phone number, password change)."
)
def update_my_profile(
    profile_in: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    client_ip = request.client.host if request.client else None
    return update_own_profile(db, current_user, profile_in, ip_address=client_ip)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
    summary="List Employees (Admin/Manager)",
    description="List employees with role-based visibility. Admin sees all company staff; Manager sees direct reports."
)
def get_users(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status_filter: Optional[UserStatus] = Query(None, alias="status", description="Filter by status"),
    manager_id: Optional[int] = Query(None, description="Filter by manager ID"),
    search: Optional[str] = Query(None, description="Search by name, email, or designation"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return list_users(
        db=db,
        current_user=current_user,
        department_id=department_id,
        role=role,
        status=status_filter,
        manager_id=manager_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get User Profile by ID",
    description="Retrieve specific user profile. Admin can view anyone; Manager can view direct reports; Employee can view self."
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    target_user = get_user_by_id(db, user_id)
    if current_user.role == UserRole.EMPLOYEE and current_user.id != user_id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Employees can only view their own profile.")
    elif current_user.role == UserRole.MANAGER and current_user.id != user_id and target_user.manager_id != current_user.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Managers can only view profiles for direct reports or themselves.")
    return build_user_response(target_user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update Employee Profile (Admin Only)",
    description="Modify user designation, department, reporting manager, role, or status."
)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    return update_user_by_admin(db, user_id, user_in, admin_user=admin_user, ip_address=client_ip)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Offboard Employee (Admin Only)",
    description="Offboard an employee by marking status as TERMINATED (or permanent deletion with hard_delete=true)."
)
def offboard_user(
    user_id: int,
    request: Request,
    hard_delete: bool = Query(False, description="Set true to permanently purge user record"),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    offboard_user_by_admin(db, user_id, admin_user=admin_user, hard_delete=hard_delete, ip_address=client_ip)
    action_type = "permanently deleted" if hard_delete else "offboarded (status set to TERMINATED)"
    return {"success": True, "message": f"Employee #{user_id} has been {action_type}."}
