from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError, ConflictError, BadRequestError
from app.core.audit import log_audit
from app.models.department import Department
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse


def build_department_response(dept: Department, db: Session) -> DepartmentResponse:
    """Format Department entity with employee count."""
    emp_count = db.query(User).filter(User.department_id == dept.id).count()
    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        description=dept.description,
        employee_count=emp_count,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


def get_department_by_id(db: Session, dept_id: int) -> Department:
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise NotFoundError(f"Department with ID {dept_id} was not found.")
    return dept


def create_department(
    db: Session,
    dept_in: DepartmentCreate,
    admin_user: User,
    ip_address: Optional[str] = None
) -> DepartmentResponse:
    existing = db.query(Department).filter(Department.name.ilike(dept_in.name.strip())).first()
    if existing:
        raise ConflictError(f"Department with name '{dept_in.name}' already exists.")

    dept = Department(
        name=dept_in.name.strip(),
        description=dept_in.description.strip() if dept_in.description else None,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    log_audit(
        db,
        action="DEPARTMENT_CREATED",
        user_id=admin_user.id,
        resource_type="department",
        resource_id=str(dept.id),
        details=f"Admin created department '{dept.name}'",
        ip_address=ip_address,
    )

    return build_department_response(dept, db)


def list_departments(db: Session, skip: int = 0, limit: int = 50) -> PaginatedResponse[DepartmentResponse]:
    query = db.query(Department)
    total = query.count()
    depts = query.order_by(Department.name.asc()).offset(skip).limit(limit).all()

    items = [build_department_response(d, db) for d in depts]
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


def update_department(
    db: Session,
    dept_id: int,
    dept_in: DepartmentUpdate,
    admin_user: User,
    ip_address: Optional[str] = None,
) -> DepartmentResponse:
    dept = get_department_by_id(db, dept_id)

    if dept_in.name is not None and dept_in.name.strip().lower() != dept.name.lower():
        existing = db.query(Department).filter(Department.name.ilike(dept_in.name.strip())).first()
        if existing and existing.id != dept.id:
            raise ConflictError(f"Department name '{dept_in.name}' is already taken.")
        dept.name = dept_in.name.strip()

    if dept_in.description is not None:
        dept.description = dept_in.description.strip()

    db.commit()
    db.refresh(dept)

    log_audit(
        db,
        action="DEPARTMENT_UPDATED",
        user_id=admin_user.id,
        resource_type="department",
        resource_id=str(dept.id),
        details=f"Admin updated department '{dept.name}'",
        ip_address=ip_address,
    )

    return build_department_response(dept, db)


def delete_department(
    db: Session,
    dept_id: int,
    admin_user: User,
    ip_address: Optional[str] = None,
) -> bool:
    dept = get_department_by_id(db, dept_id)

    # Detach or warn if employees belong to this department
    users_in_dept = db.query(User).filter(User.department_id == dept.id).count()
    if users_in_dept > 0:
        # Reassign employees to unassigned (SET NULL)
        db.query(User).filter(User.department_id == dept.id).update({User.department_id: None})

    dept_name = dept.name
    db.delete(dept)
    db.commit()

    log_audit(
        db,
        action="DEPARTMENT_DELETED",
        user_id=admin_user.id,
        resource_type="department",
        resource_id=str(dept_id),
        details=f"Admin deleted department '{dept_name}' ({users_in_dept} employees reassigned to unassigned)",
        ip_address=ip_address,
    )

    return True
