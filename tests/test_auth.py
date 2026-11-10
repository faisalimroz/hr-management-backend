def test_login_success(client, seeded_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


def test_login_invalid_password(client, seeded_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_login_nonexistent_user(client, seeded_data):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "RandomPassword!"}
    )
    assert response.status_code == 401


def test_onboard_employee_admin_success(client, admin_headers, seeded_data):
    new_user = {
        "first_name": "Charlie",
        "last_name": "Brown",
        "email": "charlie@test.com",
        "password": "CharliePassword123!",
        "role": "employee",
        "status": "active",
        "department_id": seeded_data["eng_dept"].id,
        "manager_id": seeded_data["manager"].id,
        "designation": "DevOps Engineer",
    }
    response = client.post("/api/v1/auth/register", json=new_user, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "charlie@test.com"
    assert data["full_name"] == "Charlie Brown"
    assert data["department_name"] == "Engineering"
    assert data["manager_name"] == "Manager Marcus"


def test_onboard_employee_forbidden_for_manager_and_employee(client, manager_headers, employee_headers, seeded_data):
    new_user = {
        "first_name": "Unauthorized",
        "last_name": "User",
        "email": "unauth@test.com",
        "password": "Password123!",
        "role": "employee",
    }
    # Manager attempt
    mgr_res = client.post("/api/v1/auth/register", json=new_user, headers=manager_headers)
    assert mgr_res.status_code == 403

    # Employee attempt
    emp_res = client.post("/api/v1/auth/register", json=new_user, headers=employee_headers)
    assert emp_res.status_code == 403


def test_onboard_duplicate_email(client, admin_headers, seeded_data):
    dup_user = {
        "first_name": "Duplicate",
        "last_name": "Alice",
        "email": "alice@test.com",
        "password": "Password123!",
        "role": "employee",
    }
    response = client.post("/api/v1/auth/register", json=dup_user, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
