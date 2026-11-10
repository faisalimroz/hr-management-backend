from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.audit import log_audit
from app.models.enums import AttendanceStatus, UserRole
from app.models.user import User
from app.models.attendance import AttendanceLog
from app.schemas.common import PaginatedResponse
from app.schemas.attendance import (
    AttendanceCheckIn,
    AttendanceCheckOut,
    AttendanceLogResponse,
    AttendanceSummary,
)


def build_attendance_response(log: AttendanceLog) -> AttendanceLogResponse:
    return AttendanceLogResponse(
        id=log.id,
        user_id=log.user_id,
        user_name=log.user.full_name if log.user else None,
        user_email=log.user.email if log.user else None,
        date=log.date,
        check_in_time=log.check_in_time,
        check_out_time=log.check_out_time,
        status=log.status,
        notes=log.notes,
        ip_address=log.ip_address,
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


def check_in(
    db: Session,
    current_user: User,
    check_in_data: AttendanceCheckIn,
    ip_address: Optional[str] = None,
) -> AttendanceLogResponse:
    today = date.today()
    existing_log = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.date == today
    ).first()

    now = datetime.now(timezone.utc)

    if existing_log:
        if existing_log.check_in_time is not None:
            raise BadRequestError(
                f"You have already checked in for today ({today}) at {existing_log.check_in_time.strftime('%H:%M:%S UTC')}."
            )
        existing_log.check_in_time = now
        existing_log.status = check_in_data.status or AttendanceStatus.PRESENT
        if check_in_data.notes:
            existing_log.notes = check_in_data.notes
        existing_log.ip_address = ip_address
        log_entry = existing_log
    else:
        log_entry = AttendanceLog(
            user_id=current_user.id,
            date=today,
            check_in_time=now,
            status=check_in_data.status or AttendanceStatus.PRESENT,
            notes=check_in_data.notes,
            ip_address=ip_address,
        )
        db.add(log_entry)

    db.commit()
    db.refresh(log_entry)

    log_audit(
        db,
        action="ATTENDANCE_CHECK_IN",
        user_id=current_user.id,
        resource_type="attendance",
        resource_id=str(log_entry.id),
        details=f"User {current_user.email} checked in (Status: {log_entry.status.value})",
        ip_address=ip_address,
    )

    return build_attendance_response(log_entry)


def check_out(
    db: Session,
    current_user: User,
    check_out_data: AttendanceCheckOut,
    ip_address: Optional[str] = None,
) -> AttendanceLogResponse:
    today = date.today()
    log_entry = db.query(AttendanceLog).filter(
        AttendanceLog.user_id == current_user.id,
        AttendanceLog.date == today
    ).first()

    if not log_entry or not log_entry.check_in_time:
        raise BadRequestError("Cannot check out without checking in first for today.")

    if log_entry.check_out_time is not None:
        raise BadRequestError(
            f"You have already checked out for today at {log_entry.check_out_time.strftime('%H:%M:%S UTC')}."
        )

    now = datetime.now(timezone.utc)
    log_entry.check_out_time = now

    # Append notes if present
    if check_out_data.notes:
        if log_entry.notes:
            log_entry.notes = f"{log_entry.notes} | Checkout: {check_out_data.notes}"
        else:
            log_entry.notes = f"Checkout: {check_out_data.notes}"

    # Calculate hours worked: if < 4 hours and currently marked present, adjust to half_day
    if log_entry.check_in_time:
        check_in_time_utc = log_entry.check_in_time
        if check_in_time_utc.tzinfo is None:
            check_in_time_utc = check_in_time_utc.replace(tzinfo=timezone.utc)
        duration_seconds = (now - check_in_time_utc).total_seconds()
        duration_hours = duration_seconds / 3600.0
        if duration_hours < 4.0 and log_entry.status == AttendanceStatus.PRESENT:
            log_entry.status = AttendanceStatus.HALF_DAY

    db.commit()
    db.refresh(log_entry)

    log_audit(
        db,
        action="ATTENDANCE_CHECK_OUT",
        user_id=current_user.id,
        resource_type="attendance",
        resource_id=str(log_entry.id),
        details=f"User {current_user.email} checked out (Status: {log_entry.status.value})",
        ip_address=ip_address,
    )

    return build_attendance_response(log_entry)


def get_attendance_logs(
    db: Session,
    current_user: User,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[AttendanceStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[AttendanceLogResponse]:
    """
    Query attendance records according to RBAC:
    - Employee: can ONLY view own records.
    - Manager: can view own and direct reports' records.
    - Admin: can view all records company-wide.
    """
    query = db.query(AttendanceLog).join(User, AttendanceLog.user_id == User.id)

    if current_user.role == UserRole.EMPLOYEE:
        if user_id and user_id != current_user.id:
            raise ForbiddenError("Employees are only permitted to view their own attendance logs.")
        query = query.filter(AttendanceLog.user_id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        if user_id:
            # Must be self or direct report
            target = db.query(User).filter(User.id == user_id).first()
            if not target:
                raise NotFoundError(f"User with ID {user_id} was not found.")
            if target.id != current_user.id and target.manager_id != current_user.id:
                raise ForbiddenError("Managers can only view attendance for direct reports or themselves.")
            query = query.filter(AttendanceLog.user_id == user_id)
        else:
            # Default to team + self
            query = query.filter(
                or_(
                    AttendanceLog.user_id == current_user.id,
                    User.manager_id == current_user.id
                )
            )
    else:
        # Admin
        if user_id:
            query = query.filter(AttendanceLog.user_id == user_id)

    if start_date:
        query = query.filter(AttendanceLog.date >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.date <= end_date)
    if status:
        query = query.filter(AttendanceLog.status == status)

    total = query.count()
    logs = query.order_by(AttendanceLog.date.desc(), AttendanceLog.id.desc()).offset(skip).limit(limit).all()

    items = [build_attendance_response(l) for l in logs]
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


def get_attendance_summary(
    db: Session,
    current_user: User,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> AttendanceSummary:
    """Calculate summary statistics for attendance logs."""
    target_user_id = user_id or current_user.id

    if current_user.role == UserRole.EMPLOYEE and target_user_id != current_user.id:
        raise ForbiddenError("Employees can only view their own attendance summary.")
    elif current_user.role == UserRole.MANAGER and target_user_id != current_user.id:
        target = db.query(User).filter(User.id == target_user_id).first()
        if not target or target.manager_id != current_user.id:
            raise ForbiddenError("Managers can only view attendance summary for direct reports.")

    query = db.query(AttendanceLog).filter(AttendanceLog.user_id == target_user_id)
    if start_date:
        query = query.filter(AttendanceLog.date >= start_date)
    if end_date:
        query = query.filter(AttendanceLog.date <= end_date)

    logs = query.all()
    present_count = sum(1 for l in logs if l.status == AttendanceStatus.PRESENT)
    remote_count = sum(1 for l in logs if l.status == AttendanceStatus.REMOTE)
    half_day_count = sum(1 for l in logs if l.status == AttendanceStatus.HALF_DAY)
    absent_count = sum(1 for l in logs if l.status == AttendanceStatus.ABSENT)

    return AttendanceSummary(
        total_days=len(logs),
        present_days=present_count,
        remote_days=remote_count,
        half_days=half_day_count,
        absent_days=absent_count,
    )
