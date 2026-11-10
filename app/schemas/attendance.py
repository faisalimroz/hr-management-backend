from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import AttendanceStatus


class AttendanceCheckIn(BaseModel):
    status: Optional[AttendanceStatus] = Field(default=AttendanceStatus.PRESENT, description="Check-in status (e.g. present, remote)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes or reason for remote/half-day")


class AttendanceCheckOut(BaseModel):
    notes: Optional[str] = Field(None, max_length=500, description="Optional checkout handover notes")


class AttendanceLogResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    date: date
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    status: AttendanceStatus
    notes: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummary(BaseModel):
    total_days: int
    present_days: int
    remote_days: int
    half_days: int
    absent_days: int
