def test_create_department_admin(client, admin_headers):
    dept_data = {
        "name": "Data Science",
        "description": "Machine learning and analytics infrastructure"
    }
    response = client.post("/api/v1/departments", json=dept_data, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Data Science"
    assert data["employee_count"] == 0


def test_create_department_forbidden_for_employee(client, employee_headers):
    dept_data = {"name": "Unauthorized Dept"}
    response = client.post("/api/v1/departments", json=dept_data, headers=employee_headers)
    assert response.status_code == 403


def test_list_departments(client, employee_headers):
    response = client.get("/api/v1/departments", headers=employee_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    names = [d["name"] for d in data["items"]]
    assert "Engineering" in names
    assert "Marketing" in names


def test_update_department_admin(client, admin_headers, seeded_data):
    dept_id = seeded_data["eng_dept"].id
    update_data = {"description": "Updated engineering description"}
    response = client.put(f"/api/v1/departments/{dept_id}", json=update_data, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["description"] == "Updated engineering description"


def test_delete_department_admin(client, admin_headers, seeded_data):
    dept_id = seeded_data["mkt_dept"].id
    response = client.delete(f"/api/v1/departments/{dept_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Department now 404
    get_res = client.get(f"/api/v1/departments/{dept_id}", headers=admin_headers)
    assert get_res.status_code == 404
