from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.core.security import get_password_hash
from app.models.enums import (
    UserRole,
    UserStatus,
    AttendanceStatus,
    LeaveType,
    LeaveStatus,
)
from app.models.department import Department
from app.models.user import User
from app.models.attendance import AttendanceLog
from app.models.leave import LeaveRequest
from app.models.review import PerformanceReview
from app.models.audit import AuditLog


def seed_database():
    """Seed comprehensive sample data for demonstration and testing."""
    print("Initializing database tables...")
    init_db()

    db: Session = SessionLocal()
    try:
        # Check if already seeded
        admin_check = db.query(User).filter(User.email == "admin@hrms.local").first()
        if admin_check:
            print("Database already contains seed data. Skipping seed.")
            return

        print("Seeding departments...")
        dept_eng = Department(name="Engineering", description="Software engineering, QA, DevOps, and cloud architecture")
        dept_hr = Department(name="Human Resources", description="People operations, talent acquisition, and compliance")
        dept_mkt = Department(name="Marketing", description="Brand growth, digital campaigns, and public relations")
        dept_fin = Department(name="Finance", description="Corporate accounting, budgeting, and payroll processing")
        db.add_all([dept_eng, dept_hr, dept_mkt, dept_fin])
        db.commit()

        print("Seeding users (Admin, Managers, Employees)...")
        # 1. Admin / HR Users
        admin_user = User(
            first_name="System",
            last_name="Administrator",
            email="admin@hrms.local",
            hashed_password=get_password_hash("AdminPassword123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            department_id=dept_hr.id,
            designation="VP of People Operations",
            office_location="Headquarters - New York",
            date_of_joining=date(2023, 1, 15),
            phone_number="+1-555-0100",
        )
        hr_sarah = User(
            first_name="Sarah",
            last_name="Connor",
            email="hr.sarah@hrms.local",
            hashed_password=get_password_hash("SarahPass123!"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            department_id=dept_hr.id,
            designation="HR Operations Specialist",
            office_location="Headquarters - New York",
            date_of_joining=date(2023, 6, 1),
            phone_number="+1-555-0101",
        )
        db.add_all([admin_user, hr_sarah])
        db.commit()

        # 2. Managers
        mgr_marcus = User(
            first_name="Marcus",
            last_name="Vance",
            email="manager.marcus@hrms.local",
            hashed_password=get_password_hash("ManagerPass123!"),
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
            department_id=dept_eng.id,
            manager_id=admin_user.id,
            designation="Engineering Manager",
            office_location="Tech Hub - San Francisco",
            date_of_joining=date(2023, 3, 10),
            phone_number="+1-555-0201",
        )
        mgr_elena = User(
            first_name="Elena",
            last_name="Rostova",
            email="manager.elena@hrms.local",
            hashed_password=get_password_hash("ElenaPass123!"),
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
            department_id=dept_mkt.id,
            manager_id=admin_user.id,
            designation="Marketing Director",
            office_location="Headquarters - New York",
            date_of_joining=date(2023, 4, 15),
            phone_number="+1-555-0202",
        )
        db.add_all([mgr_marcus, mgr_elena])
        db.commit()

        # 3. Employees
        emp_alice = User(
            first_name="Alice",
            last_name="Chen",
            email="alice.chen@hrms.local",
            hashed_password=get_password_hash("AlicePass123!"),
            role=UserRole.EMPLOYEE,
            status=UserStatus.ACTIVE,
            department_id=dept_eng.id,
            manager_id=mgr_marcus.id,
            designation="Senior Backend Engineer",
            office_location="Tech Hub - San Francisco",
            date_of_joining=date(2024, 1, 8),
            phone_number="+1-555-0301",
        )
        emp_bob = User(
            first_name="Bob",
            last_name="Smith",
            email="bob.smith@hrms.local",
            hashed_password=get_password_hash("BobPass123!"),
            role=UserRole.EMPLOYEE,
            status=UserStatus.ACTIVE,
            department_id=dept_eng.id,
            manager_id=mgr_marcus.id,
            designation="Full Stack Engineer",
            office_location="Remote - Austin, TX",
            date_of_joining=date(2024, 2, 1),
            phone_number="+1-555-0302",
        )
        emp_carol = User(
            first_name="Carol",
            last_name="White",
            email="carol.white@hrms.local",
            hashed_password=get_password_hash("CarolPass123!"),
            role=UserRole.EMPLOYEE,
            status=UserStatus.ACTIVE,
            department_id=dept_mkt.id,
            manager_id=mgr_elena.id,
            designation="Content Marketing Strategist",
            office_location="Headquarters - New York",
            date_of_joining=date(2024, 3, 15),
            phone_number="+1-555-0303",
        )
        emp_david = User(
            first_name="David",
            last_name="Miller",
            email="david.miller@hrms.local",
            hashed_password=get_password_hash("DavidPass123!"),
            role=UserRole.EMPLOYEE,
            status=UserStatus.ACTIVE,
            department_id=dept_fin.id,
            manager_id=admin_user.id,
            designation="Financial Analyst",
            office_location="Headquarters - New York",
            date_of_joining=date(2024, 5, 20),
            phone_number="+1-555-0304",
        )
        db.add_all([emp_alice, emp_bob, emp_carol, emp_david])
        db.commit()

        print("Seeding attendance records...")
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        # Yesterday attendance
        att_1 = AttendanceLog(
            user_id=emp_alice.id,
            date=yesterday,
            check_in_time=datetime(yesterday.year, yesterday.month, yesterday.day, 9, 0, 0, tzinfo=timezone.utc),
            check_out_time=datetime(yesterday.year, yesterday.month, yesterday.day, 17, 30, 0, tzinfo=timezone.utc),
            status=AttendanceStatus.PRESENT,
            notes="In-office full day sprint review",
            ip_address="192.168.1.100",
        )
        att_2 = AttendanceLog(
            user_id=emp_bob.id,
            date=yesterday,
            check_in_time=datetime(yesterday.year, yesterday.month, yesterday.day, 9, 15, 0, tzinfo=timezone.utc),
            check_out_time=datetime(yesterday.year, yesterday.month, yesterday.day, 17, 45, 0, tzinfo=timezone.utc),
            status=AttendanceStatus.REMOTE,
            notes="WFH Austin home office",
            ip_address="72.14.201.2",
        )
        att_3 = AttendanceLog(
            user_id=mgr_marcus.id,
            date=yesterday,
            check_in_time=datetime(yesterday.year, yesterday.month, yesterday.day, 8, 45, 0, tzinfo=timezone.utc),
            check_out_time=datetime(yesterday.year, yesterday.month, yesterday.day, 18, 0, 0, tzinfo=timezone.utc),
            status=AttendanceStatus.PRESENT,
            notes="Engineering 1-on-1s",
            ip_address="192.168.1.50",
        )
        # Today attendance
        att_today_alice = AttendanceLog(
            user_id=emp_alice.id,
            date=today,
            check_in_time=datetime(today.year, today.month, today.day, 9, 3, 0, tzinfo=timezone.utc),
            check_out_time=None,
            status=AttendanceStatus.PRESENT,
            notes="Focusing on API architecture",
            ip_address="192.168.1.100",
        )
        att_today_bob = AttendanceLog(
            user_id=emp_bob.id,
            date=today,
            check_in_time=datetime(today.year, today.month, today.day, 9, 30, 0, tzinfo=timezone.utc),
            check_out_time=None,
            status=AttendanceStatus.REMOTE,
            notes="Remote dev",
            ip_address="72.14.201.2",
        )
        db.add_all([att_1, att_2, att_3, att_today_alice, att_today_bob])
        db.commit()

        print("Seeding leave requests...")
        # Approved Sick Leave for Alice
        leave_alice_past = LeaveRequest(
            user_id=emp_alice.id,
            leave_type=LeaveType.SICK,
            start_date=two_days_ago - timedelta(days=2),
            end_date=two_days_ago - timedelta(days=1),
            reason="Recovering from acute viral flu",
            status=LeaveStatus.APPROVED,
            approved_by=mgr_marcus.id,
        )
        # Pending Annual Leave for Alice
        leave_alice_pending = LeaveRequest(
            user_id=emp_alice.id,
            leave_type=LeaveType.ANNUAL,
            start_date=today + timedelta(days=14),
            end_date=today + timedelta(days=18),
            reason="Annual family winter holiday vacation",
            status=LeaveStatus.PENDING,
        )
        # Approved Casual Leave for Bob
        leave_bob = LeaveRequest(
            user_id=emp_bob.id,
            leave_type=LeaveType.CASUAL,
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=8),
            reason="Relocation and apartment lease signing",
            status=LeaveStatus.APPROVED,
            approved_by=mgr_marcus.id,
        )
        # Rejected Leave for Carol
        leave_carol_rejected = LeaveRequest(
            user_id=emp_carol.id,
            leave_type=LeaveType.ANNUAL,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=5),
            reason="Personal trip during product launch week",
            status=LeaveStatus.REJECTED,
            approved_by=mgr_elena.id,
            rejection_reason="Major Q4 marketing campaign kickoff requires full team attendance",
        )
        db.add_all([leave_alice_past, leave_alice_pending, leave_bob, leave_carol_rejected])
        db.commit()

        print("Seeding performance reviews...")
        rev_alice = PerformanceReview(
            employee_id=emp_alice.id,
            reviewer_id=mgr_marcus.id,
            review_period="Annual 2025",
            rating=5,
            feedback="Alice is an outstanding technical pillar for our backend systems. Delivered the microservice migration two weeks ahead of schedule with zero production incidents.",
            goals="Mentor junior engineers, lead technical architecture design for 2026 platform initiatives.",
        )
        rev_bob = PerformanceReview(
            employee_id=emp_bob.id,
            reviewer_id=mgr_marcus.id,
            review_period="Annual 2025",
            rating=4,
            feedback="Bob has shown remarkable growth across both React and FastAPI stacks. Highly collaborative and consistently communicates proactively.",
            goals="Improve automated test coverage across full-stack repositories to 90%+.",
        )
        rev_carol = PerformanceReview(
            employee_id=emp_carol.id,
            reviewer_id=mgr_elena.id,
            review_period="Annual 2025",
            rating=4,
            feedback="Carol revamped our inbound blog content strategy, resulting in a 45% increase in qualified marketing leads.",
            goals="Expand international localization strategy for EMEA markets in Q1.",
        )
        db.add_all([rev_alice, rev_bob, rev_carol])
        db.commit()

        print("Seeding initial audit logs...")
        audit_1 = AuditLog(
            user_id=admin_user.id,
            action="SYSTEM_INITIALIZED",
            resource_type="system",
            details="HR Management Platform database seeded with organizational structure and baseline profiles.",
            ip_address="127.0.0.1",
        )
        db.add(audit_1)
        db.commit()

        print("\nSeed completed successfully!")
        print("=" * 60)
        print("SEED CREDENTIALS OVERVIEW:")
        print("1. Admin:    admin@hrms.local            / AdminPassword123!")
        print("   HR Admin: hr.sarah@hrms.local         / SarahPass123!")
        print("2. Manager:  manager.marcus@hrms.local   / ManagerPass123! (Engineering)")
        print("   Manager:  manager.elena@hrms.local    / ElenaPass123!   (Marketing)")
        print("3. Employee: alice.chen@hrms.local       / AlicePass123!")
        print("   Employee: bob.smith@hrms.local        / BobPass123!")
        print("   Employee: carol.white@hrms.local      / CarolPass123!")
        print("   Employee: david.miller@hrms.local     / DavidPass123!")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
