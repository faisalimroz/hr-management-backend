from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.report import HRSummaryReport
from app.services.report_service import generate_hr_summary

router = APIRouter(prefix="/reports", tags=["HR Reports & Analytics"])


@router.get(
    "/summary",
    response_model=HRSummaryReport,
    summary="Generate System-Wide HR Metrics (Admin Only)",
    description="Calculate company-wide headcount, status breakdowns, department distribution, role breakdown, pending leaves, and real-time today attendance metrics."
)
def get_hr_summary_report(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    return generate_hr_summary(db)
