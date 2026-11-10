from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_any_user, require_manager_or_admin
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.review_service import (
    create_review,
    get_employee_reviews,
    list_reviews,
)

router = APIRouter(prefix="/reviews", tags=["Performance Reviews"])


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Performance Review (Manager/Admin)",
    description="Submit a performance rating (1-5) and detailed qualitative feedback for an employee. Managers can only review direct reports."
)
def submit_review(
    review_in: ReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    client_ip = request.client.host if request.client else None
    return create_review(db, current_user, review_in, ip_address=client_ip)


@router.get(
    "/employee/{employee_id}",
    response_model=List[ReviewResponse],
    summary="Get Performance Reviews for Employee",
    description="Retrieve all performance reviews for a specific employee. Employee can see own; Manager can see team; Admin can see any."
)
def get_reviews_by_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return get_employee_reviews(db, employee_id, current_user)


@router.get(
    "/{employee_id}",
    response_model=List[ReviewResponse],
    summary="Get Reviews for Employee (Spec Alias)",
    description="Direct endpoint per project spec `/api/v1/reviews/{employee_id}`."
)
def get_reviews_by_employee_alias(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return get_employee_reviews(db, employee_id, current_user)


@router.get(
    "",
    response_model=PaginatedResponse[ReviewResponse],
    summary="List Performance Reviews",
    description="List performance reviews with role-based filtering."
)
def get_all_reviews(
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    reviewer_id: Optional[int] = Query(None, description="Filter by reviewer ID"),
    review_period: Optional[str] = Query(None, description="Filter by review period, e.g. Q1 2026"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return list_reviews(
        db=db,
        current_user=current_user,
        employee_id=employee_id,
        reviewer_id=reviewer_id,
        review_period=review_period,
        skip=skip,
        limit=limit,
    )
