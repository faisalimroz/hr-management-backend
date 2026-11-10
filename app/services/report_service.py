from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.enums import UserRole, UserStatus, AttendanceStatus, LeaveStatus
from app.models.user import User
from app.models.department import Department
from app.models.leave import LeaveRequest
from app.models.attendance import AttendanceLog
from app.schemas.report import (
    HRSummaryReport,
    DepartmentDistribution,
    RoleDistribution,
    AttendanceDailySummary,
)


def generate_hr_summary(db: Session) -> HRSummaryReport:
    total_employees = db.query(User).count()
    active_employees = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
    on_leave_employees = db.query(User).filter(User.status == UserStatus.ON_LEAVE).count()
    terminated_employees = db.query(User).filter(User.status == UserStatus.TERMINATED).count()

    total_departments = db.query(Department).count()
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == LeaveStatus.PENDING).count()

    # Department distribution
    depts = db.query(Department).all()
    dept_distribution = []
    for d in depts:
        count = db.query(User).filter(User.department_id == d.id).count()
        dept_distribution.append(
            DepartmentDistribution(
                department_id=d.id,
                department_name=d.name,
                employee_count=count,
            )
        )

    # Role distribution
    role_distribution = []
    for r in UserRole:
        count = db.query(User).filter(User.role == r).count()
        role_distribution.append(RoleDistribution(role=r.value, count=count))

    # Today's attendance
    today = date.today()
    today_logs = db.query(AttendanceLog).filter(AttendanceLog.date == today).all()
    present_cnt = sum(1 for l in today_logs if l.status == AttendanceStatus.PRESENT)
    remote_cnt = sum(1 for l in today_logs if l.status == AttendanceStatus.REMOTE)
    half_cnt = sum(1 for l in today_logs if l.status == AttendanceStatus.HALF_DAY)
    absent_cnt = sum(1 for l in today_logs if l.status == AttendanceStatus.ABSENT)

    today_attendance = AttendanceDailySummary(
        date=str(today),
        present=present_cnt,
        remote=remote_cnt,
        half_day=half_cnt,
        absent=absent_cnt,
        total_active=active_employees + on_leave_employees,
    )

    return HRSummaryReport(
        total_employees=total_employees,
        active_employees=active_employees,
        on_leave_employees=on_leave_employees,
        terminated_employees=terminated_employees,
        total_departments=total_departments,
        pending_leave_requests=pending_leaves,
        department_distribution=dept_distribution,
        role_distribution=role_distribution,
        today_attendance=today_attendance,
    )
