from sqlalchemy import Column, Integer, Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import LeaveType, LeaveStatus


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_type = Column(
        Enum(LeaveType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    reason = Column(Text, nullable=False)
    status = Column(
        Enum(LeaveStatus, values_callable=lambda x: [e.value for e in x]),
        default=LeaveStatus.PENDING,
        nullable=False,
        index=True
    )
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="leave_requests")
    approver = relationship("User", foreign_keys=[approved_by], back_populates="approved_leaves")
