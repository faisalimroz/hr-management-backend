from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_any_user
from app.models.enums import AttendanceStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.attendance import (
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceLogResponse,
    AttendanceSummary,
)
from app.services.attendance_service import (
    check_in,
    check_out,
    get_attendance_logs,
    get_attendance_summary,
)

router = APIRouter(prefix="/attendance", tags=["Attendance Management"])


@router.post(
    "/check-in",
    response_model=AttendanceLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Daily Attendance Check-In",
    description="Record today's check-in timestamp and status (present or remote). Disallows multiple check-ins on the same day."
)
def attendance_check_in(
    check_in_data: AttendanceCheckIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    client_ip = request.client.host if request.client else None
    return check_in(db, current_user, check_in_data, ip_address=client_ip)


@router.post(
    "/check-out",
    response_model=AttendanceLogResponse,
    summary="Daily Attendance Check-Out",
    description="Record today's checkout timestamp. Evaluates work duration and adjusts status to half_day if under 4 hours."
)
def attendance_check_out(
    check_out_data: AttendanceCheckOut,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    client_ip = request.client.host if request.client else None
    return check_out(db, current_user, check_out_data, ip_address=client_ip)


@router.get(
    "/logs",
    response_model=PaginatedResponse[AttendanceLogResponse],
    summary="Get Attendance Logs",
    description="List attendance records with role-based visibility. Employee sees own; Manager sees team; Admin sees company."
)
def list_attendance_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    status_filter: Optional[AttendanceStatus] = Query(None, alias="status", description="Filter by attendance status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return get_attendance_logs(
        db=db,
        current_user=current_user,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/reports",
    response_model=AttendanceSummary,
    summary="Attendance Summary Report",
    description="Calculate aggregate present, remote, half-day, and absent statistics for an employee or current user."
)
def attendance_report(
    user_id: Optional[int] = Query(None, description="Target employee ID (defaults to current user)"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return get_attendance_summary(
        db=db,
        current_user=current_user,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
