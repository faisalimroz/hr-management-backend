# Comprehensive Human Resources Management System (HRMS) Backend

A robust, enterprise-grade, secure, and scalable **Human Resources Management System (HRMS)** backend built with **Python 3.11**, **FastAPI**, **SQLAlchemy 2.0**, and **Alembic**.

The platform streamlines core HR operations across the full employee lifecycle, including role-based access control, employee onboarding/offboarding, organizational hierarchy, daily attendance tracking, leave applications and multi-tier approval workflows, performance appraisals, and executive audit logging.

---

## Table of Contents
1. [Tech Stack & Architecture](#tech-stack--architecture)
2. [User Roles & Permissions Matrix](#user-roles--permissions-matrix)
3. [Database Schema & Entity Relationship](#database-schema--entity-relationship)
4. [Project Structure](#project-structure)
5. [Getting Started & Local Setup](#getting-started--local-setup)
6. [Database Migrations (Alembic)](#database-migrations-alembic)
7. [Database Seeder & Test Accounts](#database-seeder--test-accounts)
8. [API Endpoints Reference & Examples](#api-endpoints-reference--examples)
9. [Running Automated Tests](#running-automated-tests)
10. [Docker Deployment](#docker-deployment)

---

## Tech Stack & Architecture

- **Language:** Python 3.10+ (tested on Python 3.11.9)
- **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/) (high-performance asynchronous Python REST framework)
- **ORM & Migrations:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/)
- **Database Support:** PostgreSQL (production ready via `psycopg2-binary`) & SQLite (zero-config local development and testing)
- **Validation:** Pydantic v2 with strict schemas and data normalization
- **Authentication & Security:** JWT (JSON Web Tokens) with HS256 encryption, password hashing with `passlib` / `bcrypt`
- **Documentation:** Auto-generated interactive Swagger UI (`/docs`) and ReDoc (`/redoc`)
- **Testing:** Pytest with FastAPI TestClient and isolated in-memory test database

---

## User Roles & Permissions Matrix

The platform enforces Role-Based Access Control (RBAC) via FastAPI dependencies:

| Capability / Module | Employee | Manager | Admin / HR |
|---|:---:|:---:|:---:|
| **Authentication & Profile** |
| Log in and obtain JWT access token | ✅ | ✅ | ✅ |
| View own personal profile (`/api/v1/users/me`) | ✅ | ✅ | ✅ |
| Update own profile & password (`/api/v1/users/me`) | ✅ | ✅ | ✅ |
| View team members / direct reports profiles | ❌ | ✅ | ✅ |
| View all company employee profiles | ❌ | ❌ | ✅ |
| Onboard new employees (`/api/v1/auth/register`) | ❌ | ❌ | ✅ |
| Update employee roles, dept, manager (`/api/v1/users/{id}`) | ❌ | ❌ | ✅ |
| Offboard employees (`DELETE /api/v1/users/{id}`) | ❌ | ❌ | ✅ |
| **Departments** |
| View departments and headcount | ✅ | ✅ | ✅ |
| Create, update, or delete departments | ❌ | ❌ | ✅ |
| **Attendance** |
| Daily check-in / check-out | ✅ | ✅ | ✅ |
| View own attendance log history | ✅ | ✅ | ✅ |
| View direct reports' attendance logs | ❌ | ✅ | ✅ |
| View company-wide attendance logs | ❌ | ❌ | ✅ |
| View attendance statistics summary | ✅ (self) | ✅ (team) | ✅ (all) |
| **Leave Management** |
| Submit leave request (Sick, Casual, Annual, Unpaid) | ✅ | ✅ | ✅ |
| Check own leave balances | ✅ | ✅ | ✅ |
| Check direct reports' leave balances | ❌ | ✅ | ✅ |
| Approve / reject direct reports' leave requests | ❌ | ✅ | ✅ |
| Approve / reject company-wide leave requests | ❌ | ❌ | ✅ |
| Approve own leave request | ❌ | ❌ | ❌ |
| **Performance Reviews** |
| View own received performance appraisals | ✅ | ✅ | ✅ |
| Submit performance review for direct reports | ❌ | ✅ | ✅ |
| View team members' performance reviews | ❌ | ✅ | ✅ |
| View all company performance reviews | ❌ | ❌ | ✅ |
| **Audit & Reports** |
| View system HR metrics (`/api/v1/reports/summary`) | ❌ | ❌ | ✅ |
| View immutable system audit trail (`/api/v1/audit-logs`) | ❌ | ❌ | ✅ |

---

## Database Schema & Entity Relationship

```
+-------------------------------------------------------------+
|                        departments                          |
|-------------------------------------------------------------|
| id (PK) | name (Unique) | description | created_at/updated  |
+-------------------------------------------------------------+
                               | 1
                               | N
+-------------------------------------------------------------+
|                           users                             |
|-------------------------------------------------------------|
| id (PK)           | email (Unique, Index)                   |
| first_name        | last_name                               |
| hashed_password   | role (admin | manager | employee)       |
| status (active | terminated | on_leave)                     |
| department_id (FK)| manager_id (FK, Self-reference)         |
| phone_number      | designation                             |
| office_location   | date_of_joining                         |
| created_at        | updated_at                              |
+-------------------------------------------------------------+
        | 1                     | 1                     | 1
        |                       |                       |
        | N                     | N                     | N
+--------------------+  +--------------------+  +------------------------+
|  attendance_logs   |  |   leave_requests   |  |  performance_reviews   |
|--------------------|  |--------------------|  |------------------------|
| id (PK)            |  | id (PK)            |  | id (PK)                |
| user_id (FK)       |  | user_id (FK)       |  | employee_id (FK)       |
| date (Date)        |  | leave_type (enum)  |  | reviewer_id (FK)       |
| check_in_time      |  | start_date (Date)  |  | review_period (String) |
| check_out_time     |  | end_date (Date)    |  | rating (1 - 5)         |
| status (enum)      |  | reason (Text)      |  | feedback (Text)        |
| notes (Text)       |  | status (enum)      |  | goals (Text)           |
| ip_address         |  | approved_by (FK)   |  | created_at/updated_at  |
| UQ(user_id, date)  |  | rejection_reason   |  +------------------------+
+--------------------+  | created_at/updated |
                        +--------------------+
                                   | 1
                                   | N
                        +--------------------+
                        |     audit_logs     |
                        |--------------------|
                        | id (PK)            |
                        | user_id (FK, null) |
                        | action (String)    |
                        | resource_type      |
                        | resource_id        |
                        | details (Text)     |
                        | ip_address         |
                        | created_at         |
                        +--------------------+
```

---

## Project Structure

```
c:\hr-management-backend\
├── alembic/                    # Database migration scripts
│   ├── versions/               # Individual revision files
│   └── env.py                  # Alembic runtime environment
├── app/
│   ├── config.py               # Pydantic BaseSettings configuration
│   ├── database.py             # SQLAlchemy engine & session factory
│   ├── dependencies.py         # Authentication & RBAC role checkers
│   ├── main.py                 # FastAPI application & exception handlers
│   ├── seed.py                 # Initial database seeder script
│   ├── core/
│   │   ├── audit.py            # Audit logging utility
│   │   ├── exceptions.py       # Custom HRMS HTTP exceptions
│   │   └── security.py         # JWT tokens & bcrypt password hashing
│   ├── models/
│   │   ├── attendance.py       # AttendanceLog model
│   │   ├── audit.py            # AuditLog model
│   │   ├── department.py       # Department model
│   │   ├── enums.py            # Role, Status, Leave, Attendance Enums
│   │   ├── leave.py            # LeaveRequest model
│   │   ├── review.py           # PerformanceReview model
│   │   └── user.py             # User / Employee model
│   ├── schemas/
│   │   ├── attendance.py       # Attendance Pydantic schemas
│   │   ├── audit.py            # Audit log schemas
│   │   ├── auth.py             # Login, Token schemas
│   │   ├── common.py           # Pagination & API response wrappers
│   │   ├── department.py       # Department schemas
│   │   ├── leave.py            # Leave request & balance schemas
│   │   ├── report.py           # Executive HR summary schemas
│   │   ├── review.py           # Performance review schemas
│   │   └── user.py             # User CRUD schemas
│   ├── routers/
│   │   ├── attendance.py       # /api/v1/attendance
│   │   ├── audit.py            # /api/v1/audit-logs
│   │   ├── auth.py             # /api/v1/auth
│   │   ├── departments.py      # /api/v1/departments
│   │   ├── leaves.py           # /api/v1/leaves
│   │   ├── reports.py          # /api/v1/reports
│   │   ├── reviews.py          # /api/v1/reviews
│   │   └── users.py            # /api/v1/users
│   └── services/
│       ├── attendance_service.py
│       ├── auth_service.py
│       ├── department_service.py
│       ├── leave_service.py
│       ├── report_service.py
│       ├── review_service.py
│       └── user_service.py
├── tests/                      # Automated test suite (26 passing tests)
│   ├── conftest.py             # In-memory DB & auth token fixtures
│   ├── test_attendance.py
│   ├── test_auth.py
│   ├── test_departments.py
│   ├── test_leaves.py
│   ├── test_reports_audit.py
│   ├── test_reviews.py
│   └── test_users.py
├── .env.example
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Getting Started & Local Setup

### 1. Clone & Enter Directory
```bash
cd c:\hr-management-backend
```

### 2. Create and Activate Virtual Environment
```bash
# On Linux / macOS
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell / Command Prompt)
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `.env` configuration uses SQLite (`sqlite:///./hrms.db`) which requires zero external setup. To use PostgreSQL:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/hrms_db
```

### 5. Run Database Migrations & Seed Data
```bash
# Run migrations
alembic upgrade head

# Seed initial departments, employees, attendance, and leave requests
python -m app.seed
```

### 6. Start Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000/docs](http://localhost:8000/docs)** to access the interactive Swagger documentation.

---

## Database Seeder & Test Accounts

The seed script creates initial users across all roles:

| Role | Name | Email | Password | Details |
|---|---|---|---|---|
| **Admin** | System Administrator | `admin@hrms.local` | `AdminPassword123!` | VP of People Operations |
| **Admin** | Sarah Connor | `hr.sarah@hrms.local` | `SarahPass123!` | HR Operations Specialist |
| **Manager** | Marcus Vance | `manager.marcus@hrms.local` | `ManagerPass123!` | Engineering Manager |
| **Manager** | Elena Rostova | `manager.elena@hrms.local` | `ElenaPass123!` | Marketing Director |
| **Employee** | Alice Chen | `alice.chen@hrms.local` | `AlicePass123!` | Senior Backend Engineer (Reports to Marcus) |
| **Employee** | Bob Smith | `bob.smith@hrms.local` | `BobPass123!` | Full Stack Engineer (Reports to Marcus) |
| **Employee** | Carol White | `carol.white@hrms.local` | `CarolPass123!` | Content Strategist (Reports to Elena) |
| **Employee** | David Miller | `david.miller@hrms.local` | `DavidPass123!` | Financial Analyst |

---

## API Endpoints Reference & Examples

All requests must include the header:
```http
Authorization: Bearer <your_jwt_access_token>
```
(Except for `POST /api/v1/auth/login`).

### 1. Authentication & Users
- `POST /api/v1/auth/login` - Authenticate with email/password; returns JWT token.
- `POST /api/v1/auth/register` *(Admin only)* - Onboard new employee with role, department, and reporting manager.
- `GET /api/v1/users/me` - Retrieve logged-in user profile.
- `PUT /api/v1/users/me` - Update personal contact info and password.
- `GET /api/v1/users` - List employees with filters (`department_id`, `role`, `status`, `manager_id`, `search`).
- `GET /api/v1/users/{id}` - Retrieve employee profile by ID.
- `PUT /api/v1/users/{id}` *(Admin only)* - Update employee role, department, manager, or status.
- `DELETE /api/v1/users/{id}` *(Admin only)* - Offboard employee (marks `status = terminated`).

#### Example: Login Request
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@hrms.local", "password": "AdminPassword123!"}'
```
Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": 1,
  "email": "admin@hrms.local",
  "role": "admin",
  "full_name": "System Administrator"
}
```

---

### 2. Department Management
- `POST /api/v1/departments` *(Admin only)* - Create department.
- `GET /api/v1/departments` - List departments with employee headcount.
- `GET /api/v1/departments/{id}` - Get single department details.
- `PUT /api/v1/departments/{id}` *(Admin only)* - Update department.
- `DELETE /api/v1/departments/{id}` *(Admin only)* - Delete department.

---

### 3. Attendance Management
- `POST /api/v1/attendance/check-in` - Daily check-in (prevents duplicate check-ins on same day).
- `POST /api/v1/attendance/check-out` - Daily check-out (automatically computes hours worked, sets `half_day` if < 4 hours).
- `GET /api/v1/attendance/logs` - Attendance history (Employee: self, Manager: team, Admin: all).
- `GET /api/v1/attendance/reports` - Summary report with present, remote, half-day, and absent counts.

#### Example: Check-in Request
```bash
curl -X POST "http://localhost:8000/api/v1/attendance/check-in" \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"status": "present", "notes": "Office desk 4B"}'
```

---

### 4. Leave Management Module
- `POST /api/v1/leaves` - Apply for leave (`sick`, `casual`, `annual`, `unpaid`). Validates date order, detects overlaps, checks remaining balance.
- `GET /api/v1/leaves` - List leave requests with status filters.
- `GET /api/v1/leaves/balances` - Check remaining vs used leave balances per category for the current year.
- `PUT /api/v1/leaves/{id}/status` *(Manager/Admin)* - Approve or reject leave request.

#### Example: Apply for Leave
```bash
curl -X POST "http://localhost:8000/api/v1/leaves" \
     -H "Authorization: Bearer <TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "leave_type": "annual",
       "start_date": "2026-12-15",
       "end_date": "2026-12-18",
       "reason": "Family holiday vacation"
     }'
```

#### Example: Approve Leave Request
```bash
curl -X PUT "http://localhost:8000/api/v1/leaves/1/status" \
     -H "Authorization: Bearer <MANAGER_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"status": "approved"}'
```

---

### 5. Performance Reviews Module
- `POST /api/v1/reviews` *(Manager/Admin)* - Submit review with rating (1-5), qualitative feedback, and future goals.
- `GET /api/v1/reviews/{employee_id}` - View review history for an employee.
- `GET /api/v1/reviews` - Paginated review list with filters.

---

### 6. HR Analytics & Audit Logs
- `GET /api/v1/reports/summary` *(Admin only)* - Real-time metrics on headcounts, department distribution, role breakdown, pending leaves, and today's attendance.
- `GET /api/v1/audit-logs` *(Admin only)* - Comprehensive security and operational event trail.

---

## Running Automated Tests

The backend includes a comprehensive test suite covering all modules, edge cases, date validations, and RBAC rules:

```bash
# Run pytest with verbose test logging
pytest -v
```

Output:
```
============================= test session starts =============================
collected 26 items

tests/test_attendance.py::test_check_in_and_check_out_workflow PASSED    [  3%]
tests/test_attendance.py::test_check_out_without_check_in PASSED         [  7%]
tests/test_attendance.py::test_attendance_logs_rbac PASSED               [ 11%]
tests/test_auth.py::test_login_success PASSED                            [ 15%]
tests/test_auth.py::test_login_invalid_password PASSED                   [ 19%]
tests/test_auth.py::test_login_nonexistent_user PASSED                   [ 23%]
tests/test_auth.py::test_onboard_employee_admin_success PASSED           [ 26%]
tests/test_auth.py::test_onboard_employee_forbidden_for_manager_and_employee PASSED [ 30%]
tests/test_auth.py::test_onboard_duplicate_email PASSED                  [ 34%]
tests/test_departments.py::test_create_department_admin PASSED           [ 38%]
tests/test_departments.py::test_create_department_forbidden_for_employee PASSED [ 42%]
tests/test_departments.py::test_list_departments PASSED                  [ 46%]
tests/test_departments.py::test_update_department_admin PASSED           [ 50%]
tests/test_departments.py::test_delete_department_admin PASSED           [ 53%]
tests/test_leaves.py::test_leave_apply_and_approval_workflow PASSED      [ 57%]
tests/test_leaves.py::test_manager_cannot_approve_non_report_or_self PASSED [ 61%]
tests/test_leaves.py::test_leave_balances_calculation PASSED             [ 65%]
tests/test_reports_audit.py::test_hr_summary_report_admin PASSED         [ 69%]
tests/test_reports_audit.py::test_audit_logs_admin PASSED                [ 73%]
tests/test_reviews.py::test_performance_review_submission PASSED         [ 76%]
tests/test_reviews.py::test_performance_review_forbidden_cases PASSED    [ 80%]
tests/test_users.py::test_get_current_user_profile PASSED                [ 84%]
tests/test_users.py::test_update_current_user_profile PASSED             [ 88%]
tests/test_users.py::test_list_users_rbac PASSED                         [ 92%]
tests/test_users.py::test_admin_update_user PASSED                       [ 96%]
tests/test_users.py::test_admin_offboard_user PASSED                     [100%]

======================= 26 passed in 43s =======================
```

---

## Docker Deployment

To launch the full backend with PostgreSQL via Docker Compose:

```bash
docker-compose up --build -d
```
This spins up:
1. `hrms_postgres` container running PostgreSQL 15 on port `5432` with volume persistence.
2. `hrms_backend` container running FastAPI with Uvicorn on port `8000`, which automatically executes migrations and seeds initial data.

To stop the containers:
```bash
docker-compose down
```
