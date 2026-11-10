from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.audit import log_audit
from app.models.enums import UserRole
from app.models.user import User
from app.models.review import PerformanceReview
from app.schemas.common import PaginatedResponse
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewResponse


def build_review_response(review: PerformanceReview) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        employee_id=review.employee_id,
        employee_name=review.employee.full_name if review.employee else None,
        reviewer_id=review.reviewer_id,
        reviewer_name=review.reviewer.full_name if review.reviewer else None,
        review_period=review.review_period,
        rating=review.rating,
        feedback=review.feedback,
        goals=review.goals,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def create_review(
    db: Session,
    current_user: User,
    review_in: ReviewCreate,
    ip_address: Optional[str] = None,
) -> ReviewResponse:
    target_emp = db.query(User).filter(User.id == review_in.employee_id).first()
    if not target_emp:
        raise NotFoundError(f"Employee with ID {review_in.employee_id} was not found.")

    if target_emp.id == current_user.id:
        raise BadRequestError("Self-evaluations must not be submitted as manager reviews. You cannot review yourself.")

    # Authorization Check
    if current_user.role == UserRole.MANAGER:
        if target_emp.manager_id != current_user.id:
            raise ForbiddenError("Managers can only submit performance reviews for their direct reports.")
    elif current_user.role == UserRole.EMPLOYEE:
        raise ForbiddenError("Employees are not authorized to submit performance reviews.")

    if not (1 <= review_in.rating <= 5):
        raise BadRequestError("Rating must be an integer between 1 and 5 inclusive.")

    review = PerformanceReview(
        employee_id=review_in.employee_id,
        reviewer_id=current_user.id,
        review_period=review_in.review_period.strip(),
        rating=review_in.rating,
        feedback=review_in.feedback.strip(),
        goals=review_in.goals.strip() if review_in.goals else None,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    log_audit(
        db,
        action="PERFORMANCE_REVIEW_CREATED",
        user_id=current_user.id,
        resource_type="performance_review",
        resource_id=str(review.id),
        details=f"Reviewer {current_user.email} submitted review for {target_emp.email} (Period: {review.review_period}, Rating: {review.rating}/5)",
        ip_address=ip_address,
    )

    return build_review_response(review)


def get_employee_reviews(
    db: Session,
    employee_id: int,
    current_user: User,
) -> List[ReviewResponse]:
    target_emp = db.query(User).filter(User.id == employee_id).first()
    if not target_emp:
        raise NotFoundError(f"Employee with ID {employee_id} was not found.")

    # RBAC check
    if current_user.role == UserRole.EMPLOYEE:
        if current_user.id != employee_id:
            raise ForbiddenError("Employees can only view their own performance reviews.")
    elif current_user.role == UserRole.MANAGER:
        if target_emp.id != current_user.id and target_emp.manager_id != current_user.id:
            raise ForbiddenError("Managers can only view performance reviews for direct reports or themselves.")

    reviews = db.query(PerformanceReview).filter(
        PerformanceReview.employee_id == employee_id
    ).order_by(PerformanceReview.created_at.desc()).all()

    return [build_review_response(r) for r in reviews]


def list_reviews(
    db: Session,
    current_user: User,
    employee_id: Optional[int] = None,
    reviewer_id: Optional[int] = None,
    review_period: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[ReviewResponse]:
    query = db.query(PerformanceReview).join(User, PerformanceReview.employee_id == User.id)

    if current_user.role == UserRole.EMPLOYEE:
        query = query.filter(PerformanceReview.employee_id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        query = query.filter(
            or_(
                PerformanceReview.reviewer_id == current_user.id,
                PerformanceReview.employee_id == current_user.id,
                User.manager_id == current_user.id
            )
        )
        if employee_id:
            target = db.query(User).filter(User.id == employee_id).first()
            if not target or (target.id != current_user.id and target.manager_id != current_user.id):
                raise ForbiddenError("Managers cannot view reviews outside their team.")
            query = query.filter(PerformanceReview.employee_id == employee_id)
    else:
        # Admin
        if employee_id:
            query = query.filter(PerformanceReview.employee_id == employee_id)

    if reviewer_id:
        query = query.filter(PerformanceReview.reviewer_id == reviewer_id)
    if review_period:
        query = query.filter(PerformanceReview.review_period == review_period)

    total = query.count()
    reviews = query.order_by(PerformanceReview.created_at.desc()).offset(skip).limit(limit).all()

    items = [build_review_response(r) for r in reviews]
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)
