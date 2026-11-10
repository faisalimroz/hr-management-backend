from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_admin, require_any_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.services.department_service import (
    create_department,
    get_department_by_id,
    list_departments,
    update_department,
    delete_department,
    build_department_response,
)

router = APIRouter(prefix="/departments", tags=["Departments Organization"])


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Department (Admin Only)",
    description="Create a new company department entity."
)
def create_dept(
    dept_in: DepartmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    return create_department(db, dept_in, admin_user=admin_user, ip_address=client_ip)


@router.get(
    "",
    response_model=PaginatedResponse[DepartmentResponse],
    summary="List Departments",
    description="Retrieve all departments with associated employee headcounts."
)
def get_depts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    return list_departments(db, skip=skip, limit=limit)


@router.get(
    "/{dept_id}",
    response_model=DepartmentResponse,
    summary="Get Department by ID",
    description="Fetch single department information."
)
def get_dept(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_user),
):
    dept = get_department_by_id(db, dept_id)
    return build_department_response(dept, db)


@router.put(
    "/{dept_id}",
    response_model=DepartmentResponse,
    summary="Update Department (Admin Only)",
    description="Update department name or description."
)
def update_dept(
    dept_id: int,
    dept_in: DepartmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    return update_department(db, dept_id, dept_in, admin_user=admin_user, ip_address=client_ip)


@router.delete(
    "/{dept_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Department (Admin Only)",
    description="Remove department entity. Employees assigned to this department will have their department reset to None."
)
def delete_dept(
    dept_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    client_ip = request.client.host if request.client else None
    delete_department(db, dept_id, admin_user=admin_user, ip_address=client_ip)
    return {"success": True, "message": f"Department #{dept_id} was successfully deleted."}
