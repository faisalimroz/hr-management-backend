from datetime import date
from typing import List, Optional
from sqlalchemy import or_, extract
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.audit import log_audit
from app.models.enums import LeaveType, LeaveStatus, UserRole, UserStatus
from app.models.user import User
from app.models.leave import LeaveRequest
from app.schemas.common import PaginatedResponse
from app.schemas.leave import (
    LeaveRequestCreate,
    LeaveStatusUpdate,
    LeaveResponse,
    LeaveBalanceItem,
    LeaveBalanceResponse,
)

# Standard Annual Leave Entitlement (days per calendar year)
LEAVE_ALLOWANCES = {
    LeaveType.ANNUAL: 15,
    LeaveType.SICK: 12,
    LeaveType.CASUAL: 10,
    LeaveType.UNPAID: 365,
}


def build_leave_response(leave: LeaveRequest) -> LeaveResponse:
    total_days = (leave.end_date - leave.start_date).days + 1
    return LeaveResponse(
        id=leave.id,
        user_id=leave.user_id,
        user_name=leave.user.full_name if leave.user else None,
        user_email=leave.user.email if leave.user else None,
        leave_type=leave.leave_type,
        start_date=leave.start_date,
        end_date=leave.end_date,
        total_days=total_days,
        reason=leave.reason,
        status=leave.status,
        approved_by=leave.approved_by,
        approver_name=leave.approver.full_name if leave.approver else None,
        rejection_reason=leave.rejection_reason,
        created_at=leave.created_at,
        updated_at=leave.updated_at,
    )


def calculate_leave_balances(db: Session, user_id: int, year: Optional[int] = None) -> LeaveBalanceResponse:
    target_year = year or date.today().year
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError(f"User with ID {user_id} was not found.")

    # Fetch approved leaves for the year
    approved_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status == LeaveStatus.APPROVED,
        extract("year", LeaveRequest.start_date) == target_year
    ).all()

    # Aggregate used days by type
    used_days_map = {lt: 0 for lt in LeaveType}
    for leave in approved_leaves:
        days = (leave.end_date - leave.start_date).days + 1
        used_days_map[leave.leave_type] = used_days_map.get(leave.leave_type, 0) + days

    balances: List[LeaveBalanceItem] = []
    for lt in [LeaveType.ANNUAL, LeaveType.SICK, LeaveType.CASUAL, LeaveType.UNPAID]:
        allowance = LEAVE_ALLOWANCES[lt]
        used = used_days_map.get(lt, 0)
        remaining = max(0, allowance - used) if lt != LeaveType.UNPAID else 365
        balances.append(
            LeaveBalanceItem(
                leave_type=lt,
                total_allowance=allowance,
                used_days=used,
                remaining_days=remaining,
            )
        )

    return LeaveBalanceResponse(
        user_id=user.id,
        user_name=user.full_name,
        year=target_year,
        balances=balances,
    )


def apply_leave(
    db: Session,
    current_user: User,
    leave_in: LeaveRequestCreate,
    ip_address: Optional[str] = None,
) -> LeaveResponse:
    if leave_in.start_date > leave_in.end_date:
        raise BadRequestError("Leave start date cannot be after end date.")

    # Check for overlapping active leaves (pending or approved)
    overlapping = db.query(LeaveRequest).filter(
        LeaveRequest.user_id == current_user.id,
        LeaveRequest.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
        LeaveRequest.start_date <= leave_in.end_date,
        LeaveRequest.end_date >= leave_in.start_date,
    ).first()

    if overlapping:
        raise ConflictError(
            f"You already have a {overlapping.status.value} leave request from {overlapping.start_date} to {overlapping.end_date}."
        )

    # Check balance if not unpaid leave
    requested_days = (leave_in.end_date - leave_in.start_date).days + 1
    if leave_in.leave_type != LeaveType.UNPAID:
        balance_info = calculate_leave_balances(db, current_user.id, leave_in.start_date.year)
        item = next((b for b in balance_info.balances if b.leave_type == leave_in.leave_type), None)
        if item and requested_days > item.remaining_days:
            raise BadRequestError(
                f"Insufficient {leave_in.leave_type.value} leave balance. "
                f"Requested: {requested_days} days, Remaining: {item.remaining_days} days."
            )

    leave_request = LeaveRequest(
        user_id=current_user.id,
        leave_type=leave_in.leave_type,
        start_date=leave_in.start_date,
        end_date=leave_in.end_date,
        reason=leave_in.reason.strip(),
        status=LeaveStatus.PENDING,
    )
    db.add(leave_request)
    db.commit()
    db.refresh(leave_request)

    log_audit(
        db,
        action="LEAVE_REQUESTED",
        user_id=current_user.id,
        resource_type="leave_request",
        resource_id=str(leave_request.id),
        details=f"User {current_user.email} applied for {leave_request.leave_type.value} leave ({requested_days} days: {leave_request.start_date} to {leave_request.end_date})",
        ip_address=ip_address,
    )

    return build_leave_response(leave_request)


def list_leaves(
    db: Session,
    current_user: User,
    user_id: Optional[int] = None,
    status: Optional[LeaveStatus] = None,
    leave_type: Optional[LeaveType] = None,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[LeaveResponse]:
    """
    List leaves by role:
    - Employee: can only view own leave requests.
    - Manager: can view own and direct reports' leave requests.
    - Admin: can view all company leave requests.
    """
    query = db.query(LeaveRequest).join(User, LeaveRequest.user_id == User.id)

    if current_user.role == UserRole.EMPLOYEE:
        if user_id and user_id != current_user.id:
            raise ForbiddenError("Employees are only permitted to view their own leave requests.")
        query = query.filter(LeaveRequest.user_id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        if user_id:
            target = db.query(User).filter(User.id == user_id).first()
            if not target:
                raise NotFoundError(f"User with ID {user_id} was not found.")
            if target.id != current_user.id and target.manager_id != current_user.id:
                raise ForbiddenError("Managers can only view leave requests for their direct reports or themselves.")
            query = query.filter(LeaveRequest.user_id == user_id)
        else:
            query = query.filter(
                or_(
                    LeaveRequest.user_id == current_user.id,
                    User.manager_id == current_user.id
                )
            )
    else:
        # Admin
        if user_id:
            query = query.filter(LeaveRequest.user_id == user_id)

    if status:
        query = query.filter(LeaveRequest.status == status)
    if leave_type:
        query = query.filter(LeaveRequest.leave_type == leave_type)

    total = query.count()
    leaves = query.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit).all()

    items = [build_leave_response(l) for l in leaves]
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


def update_leave_status(
    db: Session,
    leave_id: int,
    status_in: LeaveStatusUpdate,
    current_user: User,
    ip_address: Optional[str] = None,
) -> LeaveResponse:
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise NotFoundError(f"Leave request with ID {leave_id} was not found.")

    if leave.status != LeaveStatus.PENDING:
        raise BadRequestError(f"Leave request #{leave_id} has already been {leave.status.value}.")

    # Authorization Check
    applicant = leave.user
    if current_user.role == UserRole.MANAGER:
        if applicant.manager_id != current_user.id:
            raise ForbiddenError("Managers can only approve or reject leaves for their direct reports.")
        if applicant.id == current_user.id:
            raise ForbiddenError("Managers cannot approve their own leave requests.")
    elif current_user.role == UserRole.EMPLOYEE:
        raise ForbiddenError("Employees are not authorized to approve or reject leave requests.")

    leave.status = status_in.status
    leave.approved_by = current_user.id
    if status_in.status == LeaveStatus.REJECTED and status_in.rejection_reason:
        leave.rejection_reason = status_in.rejection_reason.strip()

    # If approved and leave is currently active today, update user status to ON_LEAVE
    today = date.today()
    if status_in.status == LeaveStatus.APPROVED and leave.start_date <= today <= leave.end_date:
        applicant.status = UserStatus.ON_LEAVE

    db.commit()
    db.refresh(leave)

    log_audit(
        db,
        action=f"LEAVE_{status_in.status.value.upper()}",
        user_id=current_user.id,
        resource_type="leave_request",
        resource_id=str(leave.id),
        details=f"{current_user.role.value.capitalize()} {current_user.email} marked leave #{leave.id} as {status_in.status.value}",
        ip_address=ip_address,
    )

    return build_leave_response(leave)
