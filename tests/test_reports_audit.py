def test_hr_summary_report_admin(client, admin_headers, employee_headers):
    # Admin accesses summary report -> 200
    res_admin = client.get("/api/v1/reports/summary", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert "total_employees" in data
    assert "active_employees" in data
    assert "department_distribution" in data
    assert "role_distribution" in data
    assert "today_attendance" in data

    # Employee accesses summary report -> 403 Forbidden
    res_emp = client.get("/api/v1/reports/summary", headers=employee_headers)
    assert res_emp.status_code == 403


def test_audit_logs_admin(client, admin_headers, manager_headers):
    # Admin views audit logs -> 200
    res_admin = client.get("/api/v1/audit-logs", headers=admin_headers)
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert "items" in data
    assert data["total"] >= 1

    # Manager attempts to view audit logs -> 403 Forbidden
    res_mgr = client.get("/api/v1/audit-logs", headers=manager_headers)
    assert res_mgr.status_code == 403
