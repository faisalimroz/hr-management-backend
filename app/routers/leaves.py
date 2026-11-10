from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_any_user, require_manager_or_admin
from app.models.enums import LeaveType, LeaveStatus, UserRole
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.leave import (
    LeaveRequestCreate,
    LeaveStatusUpdate,
    LeaveResponse,
    LeaveBalanceResponse,
)
from app.services.leave_service import (
    apply_leave,
    list_leaves,
    calculate_leave_balances,
    update_leave_status,
)

router = APIRouter(prefix="/leaves", tags=["Leave Management"])


@router.post(
    "",
    response_model=LeaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Leave Request",
    description="Submit a new leave request (Sick, Casual, Annual, Unpaid). Automatically verifies leave balance and dates overlap."
)
def submit_leave(
    leave_in: LeaveRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    client_ip = request.client.host if request.client else None
    return apply_leave(db, current_user, leave_in, ip_address=client_ip)


@router.get(
    "",
    response_model=PaginatedResponse[LeaveResponse],
    summary="List Leave Requests",
    description="Retrieve leave requests based on role. Employee views own; Manager views direct reports; Admin views company-wide."
)
def get_leaves(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status_filter: Optional[LeaveStatus] = Query(None, alias="status", description="Filter by status (pending, approved, rejected)"),
    leave_type: Optional[LeaveType] = Query(None, description="Filter by leave type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return list_leaves(
        db=db,
        current_user=current_user,
        user_id=user_id,
        status=status_filter,
        leave_type=leave_type,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/balances",
    response_model=LeaveBalanceResponse,
    summary="Get Leave Balances",
    description="View total entitlement, used days, and remaining balances per leave category."
)
def get_leave_balances(
    user_id: Optional[int] = Query(None, description="Target user ID (defaults to self)"),
    year: Optional[int] = Query(None, description="Target calendar year (defaults to current year)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    target_id = user_id or current_user.id
    if current_user.role == UserRole.EMPLOYEE and target_id != current_user.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Employees can only view their own leave balances.")
    elif current_user.role == UserRole.MANAGER and target_id != current_user.id:
        from app.models.user import User as UserModel
        target = db.query(UserModel).filter(UserModel.id == target_id).first()
        if not target or target.manager_id != current_user.id:
            from app.core.exceptions import ForbiddenError
            raise ForbiddenError("Managers can only view leave balances for direct reports.")

    return calculate_leave_balances(db, user_id=target_id, year=year)


@router.put(
    "/{leave_id}/status",
    response_model=LeaveResponse,
    summary="Approve or Reject Leave Request (Manager/Admin)",
    description="Update leave request status to 'approved' or 'rejected'. Managers can only action leaves from direct reports."
)
def update_status(
    leave_id: int,
    status_in: LeaveStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    client_ip = request.client.host if request.client else None
    return update_leave_status(db, leave_id, status_in, current_user=current_user, ip_address=client_ip)
