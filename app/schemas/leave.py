from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict
from app.models.enums import LeaveType, LeaveStatus


class LeaveRequestCreate(BaseModel):
    leave_type: LeaveType = Field(..., examples=[LeaveType.ANNUAL])
    start_date: date = Field(..., examples=["2026-12-01"])
    end_date: date = Field(..., examples=["2026-12-05"])
    reason: str = Field(..., min_length=5, max_length=1000, examples=["Attending family wedding"])

    @model_validator(mode="after")
    def check_dates(self) -> "LeaveRequestCreate":
        if self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self


class LeaveStatusUpdate(BaseModel):
    status: LeaveStatus = Field(..., description="Target status: approved or rejected")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Mandatory or recommended if rejected")

    @model_validator(mode="after")
    def check_status_valid(self) -> "LeaveStatusUpdate":
        if self.status not in (LeaveStatus.APPROVED, LeaveStatus.REJECTED):
            raise ValueError("Status must be either 'approved' or 'rejected'")
        return self


class LeaveResponse(BaseModel):
    id: int
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    leave_type: LeaveType
    start_date: date
    end_date: date
    total_days: int
    reason: str
    status: LeaveStatus
    approved_by: Optional[int] = None
    approver_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeaveBalanceItem(BaseModel):
    leave_type: LeaveType
    total_allowance: int
    used_days: int
    remaining_days: int


class LeaveBalanceResponse(BaseModel):
    user_id: int
    user_name: str
    year: int
    balances: List[LeaveBalanceItem]
