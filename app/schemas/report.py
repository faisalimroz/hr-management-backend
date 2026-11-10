from typing import Dict, List
from pydantic import BaseModel


class DepartmentDistribution(BaseModel):
    department_id: int
    department_name: str
    employee_count: int


class RoleDistribution(BaseModel):
    role: str
    count: int


class AttendanceDailySummary(BaseModel):
    date: str
    present: int
    remote: int
    half_day: int
    absent: int
    total_active: int


class HRSummaryReport(BaseModel):
    total_employees: int
    active_employees: int
    on_leave_employees: int
    terminated_employees: int
    total_departments: int
    pending_leave_requests: int
    department_distribution: List[DepartmentDistribution]
    role_distribution: List[RoleDistribution]
    today_attendance: AttendanceDailySummary
