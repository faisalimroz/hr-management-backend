from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.enums import UserRole, UserStatus


class UserBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100, examples=["John"])
    last_name: str = Field(..., min_length=1, max_length=100, examples=["Doe"])
    email: EmailStr = Field(..., examples=["john.doe@hrms.local"])
    phone_number: Optional[str] = Field(None, max_length=50, examples=["+1234567890"])
    designation: Optional[str] = Field(None, max_length=100, examples=["Senior Software Engineer"])
    office_location: Optional[str] = Field(None, max_length=100, examples=["Headquarters - New York"])


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100, examples=["SecurePass123!"])
    role: UserRole = Field(default=UserRole.EMPLOYEE, examples=[UserRole.EMPLOYEE])
    status: UserStatus = Field(default=UserStatus.ACTIVE, examples=[UserStatus.ACTIVE])
    department_id: Optional[int] = Field(None, examples=[1])
    manager_id: Optional[int] = Field(None, examples=[2])
    date_of_joining: Optional[date] = Field(default_factory=date.today)


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    designation: Optional[str] = Field(None, max_length=100)
    office_location: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    date_of_joining: Optional[date] = None
    password: Optional[str] = Field(None, min_length=6, max_length=100)


class UserProfileUpdate(BaseModel):
    """Fields that employees can update on their own profile."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=50)
    current_password: Optional[str] = Field(None, min_length=6)
    new_password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    id: int
    full_name: str
    role: UserRole
    status: UserStatus
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    date_of_joining: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    id: int
    full_name: str
    email: str
    role: UserRole
    designation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
