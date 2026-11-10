from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.security import verify_password, get_password_hash
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.core.audit import log_audit
from app.models.enums import UserRole, UserStatus
from app.models.user import User
from app.models.department import Department
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserUpdate, UserProfileUpdate, UserResponse
from app.services.auth_service import build_user_response


def get_user_by_id(db: Session, user_id: int) -> User:
    """Retrieve user entity by primary key ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(f"User with ID {user_id} was not found.")
    return user


def list_users(
    db: Session,
    current_user: User,
    department_id: Optional[int] = None,
    role: Optional[UserRole] = None,
    status: Optional[UserStatus] = None,
    manager_id: Optional[int] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[UserResponse]:
    """
    List users with RBAC filtering.
    - Admin: Can list all company users with full filters.
    - Manager: Restricted to self and direct reports (or team members).
    - Employee: Restricted to viewing self.
    """
    query = db.query(User)

    if current_user.role == UserRole.EMPLOYEE:
        # Employees can only view themselves in the list
        query = query.filter(User.id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        # Managers can see themselves and their direct reports
        query = query.filter(
            or_(
                User.id == current_user.id,
                User.manager_id == current_user.id
            )
        )
        if manager_id and manager_id != current_user.id:
            raise ForbiddenError("Managers can only filter by their own team ID.")
    else:
        # Admin can filter by manager_id freely
        if manager_id is not None:
            query = query.filter(User.manager_id == manager_id)

    # Common filters
    if department_id is not None:
        query = query.filter(User.department_id == department_id)
    if role is not None:
        query = query.filter(User.role == role)
    if status is not None:
        query = query.filter(User.status == status)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_pattern),
                User.last_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.designation.ilike(search_pattern),
            )
        )

    total = query.count()
    users = query.order_by(User.id.asc()).offset(skip).limit(limit).all()

    items = [build_user_response(u) for u in users]
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


def update_own_profile(
    db: Session,
    current_user: User,
    profile_in: UserProfileUpdate,
    ip_address: Optional[str] = None,
) -> UserResponse:
    """Allow an employee to update their personal details and password."""
    if profile_in.first_name is not None:
        current_user.first_name = profile_in.first_name.strip()
    if profile_in.last_name is not None:
        current_user.last_name = profile_in.last_name.strip()
    if profile_in.phone_number is not None:
        current_user.phone_number = profile_in.phone_number.strip()

    if profile_in.new_password:
        if not profile_in.current_password:
            raise BadRequestError("Current password is required to set a new password.")
        if not verify_password(profile_in.current_password, current_user.hashed_password):
            raise BadRequestError("Current password entered is incorrect.")
        current_user.hashed_password = get_password_hash(profile_in.new_password)

    db.commit()
    db.refresh(current_user)

    log_audit(
        db,
        action="USER_PROFILE_UPDATED",
        user_id=current_user.id,
        resource_type="user",
        resource_id=str(current_user.id),
        details="User updated personal contact information",
        ip_address=ip_address,
    )

    return build_user_response(current_user)


def update_user_by_admin(
    db: Session,
    user_id: int,
    user_in: UserUpdate,
    admin_user: User,
    ip_address: Optional[str] = None,
) -> UserResponse:
    """Admin update of employee profile (lifecycle management, roles, departments)."""
    target_user = get_user_by_id(db, user_id)

    # Validate department if changed
    if user_in.department_id is not None:
        dept = db.query(Department).filter(Department.id == user_in.department_id).first()
        if not dept:
            raise NotFoundError(f"Department with ID {user_in.department_id} not found.")
        target_user.department_id = user_in.department_id

    # Validate manager if changed
    if user_in.manager_id is not None:
        if user_in.manager_id == target_user.id:
            raise BadRequestError("A user cannot be designated as their own manager.")
        mgr = db.query(User).filter(User.id == user_in.manager_id).first()
        if not mgr:
            raise NotFoundError(f"Manager with ID {user_in.manager_id} not found.")
        target_user.manager_id = user_in.manager_id

    if user_in.first_name is not None:
        target_user.first_name = user_in.first_name.strip()
    if user_in.last_name is not None:
        target_user.last_name = user_in.last_name.strip()
    if user_in.phone_number is not None:
        target_user.phone_number = user_in.phone_number.strip()
    if user_in.designation is not None:
        target_user.designation = user_in.designation.strip()
    if user_in.office_location is not None:
        target_user.office_location = user_in.office_location.strip()
    if user_in.role is not None:
        target_user.role = user_in.role
    if user_in.status is not None:
        target_user.status = user_in.status
    if user_in.date_of_joining is not None:
        target_user.date_of_joining = user_in.date_of_joining
    if user_in.password:
        target_user.hashed_password = get_password_hash(user_in.password)

    db.commit()
    db.refresh(target_user)

    log_audit(
        db,
        action="USER_UPDATED_BY_ADMIN",
        user_id=admin_user.id,
        resource_type="user",
        resource_id=str(target_user.id),
        details=f"Admin updated user {target_user.email} (Role: {target_user.role.value}, Status: {target_user.status.value})",
        ip_address=ip_address,
    )

    return build_user_response(target_user)


def offboard_user_by_admin(
    db: Session,
    user_id: int,
    admin_user: User,
    hard_delete: bool = False,
    ip_address: Optional[str] = None,
) -> bool:
    """Offboard employee by setting status to TERMINATED, or permanently deleting."""
    target_user = get_user_by_id(db, user_id)

    if target_user.id == admin_user.id:
        raise BadRequestError("Administrators cannot offboard/delete their own account.")

    if hard_delete:
        db.delete(target_user)
        action_name = "USER_PERMANENTLY_DELETED"
        details_msg = f"Admin permanently deleted user {target_user.email}"
    else:
        target_user.status = UserStatus.TERMINATED
        action_name = "USER_OFFBOARDED"
        details_msg = f"Admin offboarded user {target_user.email} (Status set to TERMINATED)"

    db.commit()

    log_audit(
        db,
        action=action_name,
        user_id=admin_user.id,
        resource_type="user",
        resource_id=str(user_id),
        details=details_msg,
        ip_address=ip_address,
    )

    return True
