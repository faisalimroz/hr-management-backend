from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ReviewCreate(BaseModel):
    employee_id: int = Field(..., examples=[3], description="User ID of employee receiving the review")
    review_period: str = Field(..., min_length=2, max_length=50, examples=["Q1 2026", "Annual 2025"])
    rating: int = Field(..., ge=1, le=5, examples=[4], description="Score from 1 (unsatisfactory) to 5 (exceptional)")
    feedback: str = Field(..., min_length=5, max_length=3000, examples=["Consistently exceeds delivery expectations."])
    goals: Optional[str] = Field(None, max_length=2000, examples=["Achieve AWS Solutions Architect certification"])


class ReviewUpdate(BaseModel):
    review_period: Optional[str] = Field(None, min_length=2, max_length=50)
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback: Optional[str] = Field(None, min_length=5, max_length=3000)
    goals: Optional[str] = Field(None, max_length=2000)


class ReviewResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    reviewer_id: int
    reviewer_name: Optional[str] = None
    review_period: str
    rating: int
    feedback: str
    goals: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
