from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import UserRole, UserStatus


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.EMPLOYEE, nullable=False, index=True)
    status = Column(Enum(UserStatus, values_callable=lambda x: [e.value for e in x]), default=UserStatus.ACTIVE, nullable=False, index=True)

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    phone_number = Column(String(50), nullable=True)
    designation = Column(String(100), nullable=True)
    office_location = Column(String(100), nullable=True)
    date_of_joining = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    department = relationship("Department", back_populates="users")
    manager = relationship("User", remote_side=[id], backref="direct_reports")
    attendance_logs = relationship("AttendanceLog", back_populates="user", cascade="all, delete-orphan")
    leave_requests = relationship(
        "LeaveRequest",
        foreign_keys="[LeaveRequest.user_id]",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    approved_leaves = relationship(
        "LeaveRequest",
        foreign_keys="[LeaveRequest.approved_by]",
        back_populates="approver"
    )
    reviews_received = relationship(
        "PerformanceReview",
        foreign_keys="[PerformanceReview.employee_id]",
        back_populates="employee",
        cascade="all, delete-orphan"
    )
    reviews_given = relationship(
        "PerformanceReview",
        foreign_keys="[PerformanceReview.reviewer_id]",
        back_populates="reviewer"
    )
    audit_logs = relationship("AuditLog", back_populates="user")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
