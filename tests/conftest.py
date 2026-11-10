import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.core.security import get_password_hash
from app.models.enums import UserRole, UserStatus
from app.models.department import Department
from app.models.user import User

# In-memory SQLite engine for fast and isolated unit tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_data(db):
    # Department
    eng_dept = Department(name="Engineering", description="Software development")
    mkt_dept = Department(name="Marketing", description="Marketing and growth")
    db.add_all([eng_dept, mkt_dept])
    db.commit()

    # Admin User
    admin = User(
        first_name="Admin",
        last_name="User",
        email="admin@test.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        department_id=eng_dept.id,
        date_of_joining=date(2023, 1, 1),
    )
    db.add(admin)
    db.commit()

    # Manager User
    manager = User(
        first_name="Manager",
        last_name="Marcus",
        email="manager@test.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        role=UserRole.MANAGER,
        status=UserStatus.ACTIVE,
        department_id=eng_dept.id,
        manager_id=admin.id,
        date_of_joining=date(2023, 2, 1),
    )
    other_manager = User(
        first_name="Other",
        last_name="Manager",
        email="other_manager@test.com",
        hashed_password=get_password_hash("OtherPass123!"),
        role=UserRole.MANAGER,
        status=UserStatus.ACTIVE,
        department_id=mkt_dept.id,
        date_of_joining=date(2023, 3, 1),
    )
    db.add_all([manager, other_manager])
    db.commit()

    # Direct Report Employee
    employee = User(
        first_name="Alice",
        last_name="Employee",
        email="alice@test.com",
        hashed_password=get_password_hash("AlicePass123!"),
        role=UserRole.EMPLOYEE,
        status=UserStatus.ACTIVE,
        department_id=eng_dept.id,
        manager_id=manager.id,
        date_of_joining=date(2024, 1, 1),
    )
    # Another Employee (reporting to other_manager)
    bob = User(
        first_name="Bob",
        last_name="Worker",
        email="bob@test.com",
        hashed_password=get_password_hash("BobPass123!"),
        role=UserRole.EMPLOYEE,
        status=UserStatus.ACTIVE,
        department_id=mkt_dept.id,
        manager_id=other_manager.id,
        date_of_joining=date(2024, 1, 1),
    )
    db.add_all([employee, bob])
    db.commit()

    return {
        "admin": admin,
        "manager": manager,
        "other_manager": other_manager,
        "employee": employee,
        "bob": bob,
        "eng_dept": eng_dept,
        "mkt_dept": mkt_dept,
    }


def get_token(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def admin_headers(client, seeded_data):
    token = get_token(client, "admin@test.com", "AdminPass123!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client, seeded_data):
    token = get_token(client, "manager@test.com", "ManagerPass123!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_manager_headers(client, seeded_data):
    token = get_token(client, "other_manager@test.com", "OtherPass123!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def employee_headers(client, seeded_data):
    token = get_token(client, "alice@test.com", "AlicePass123!")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bob_headers(client, seeded_data):
    token = get_token(client, "bob@test.com", "BobPass123!")
    return {"Authorization": f"Bearer {token}"}
