def test_get_current_user_profile(client, employee_headers):
    response = client.get("/api/v1/users/me", headers=employee_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "alice@test.com"
    assert data["full_name"] == "Alice Employee"
    assert data["role"] == "employee"


def test_update_current_user_profile(client, employee_headers):
    update_payload = {
        "first_name": "Alicia",
        "phone_number": "+1-555-9988"
    }
    response = client.put("/api/v1/users/me", json=update_payload, headers=employee_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Alicia"
    assert data["phone_number"] == "+1-555-9988"


def test_list_users_rbac(client, admin_headers, manager_headers, employee_headers, seeded_data):
    # Admin sees all employees
    res_admin = client.get("/api/v1/users", headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["total"] >= 5

    # Manager Marcus sees self and Alice (his direct report)
    res_mgr = client.get("/api/v1/users", headers=manager_headers)
    assert res_mgr.status_code == 200
    mgr_users = res_mgr.json()["items"]
    mgr_emails = [u["email"] for u in mgr_users]
    assert "manager@test.com" in mgr_emails
    assert "alice@test.com" in mgr_emails
    assert "bob@test.com" not in mgr_emails  # Bob reports to other_manager

    # Employee Alice sees only herself
    res_emp = client.get("/api/v1/users", headers=employee_headers)
    assert res_emp.status_code == 200
    emp_users = res_emp.json()["items"]
    assert len(emp_users) == 1
    assert emp_users[0]["email"] == "alice@test.com"


def test_admin_update_user(client, admin_headers, seeded_data):
    alice_id = seeded_data["employee"].id
    update_payload = {
        "designation": "Staff Engineer",
        "role": "manager"
    }
    response = client.put(f"/api/v1/users/{alice_id}", json=update_payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["designation"] == "Staff Engineer"
    assert data["role"] == "manager"


def test_admin_offboard_user(client, admin_headers, seeded_data):
    bob_id = seeded_data["bob"].id
    response = client.delete(f"/api/v1/users/{bob_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # User profile status is now TERMINATED
    profile_res = client.get(f"/api/v1/users/{bob_id}", headers=admin_headers)
    assert profile_res.status_code == 200
    assert profile_res.json()["status"] == "terminated"
