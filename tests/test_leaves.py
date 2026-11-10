from datetime import date, timedelta


def test_leave_apply_and_approval_workflow(client, employee_headers, manager_headers, seeded_data):
    today = date.today()
    start_date = str(today + timedelta(days=20))
    end_date = str(today + timedelta(days=22))

    # 1. Alice applies for Casual leave
    leave_payload = {
        "leave_type": "casual",
        "start_date": start_date,
        "end_date": end_date,
        "reason": "Personal family event out of town",
    }
    res_apply = client.post("/api/v1/leaves", json=leave_payload, headers=employee_headers)
    assert res_apply.status_code == 201
    leave_data = res_apply.json()
    assert leave_data["status"] == "pending"
    assert leave_data["total_days"] == 3
    leave_id = leave_data["id"]

    # 2. Overlapping leave request rejection -> 409
    res_overlap = client.post("/api/v1/leaves", json=leave_payload, headers=employee_headers)
    assert res_overlap.status_code == 409
    assert res_overlap.json()["error"]["code"] == "CONFLICT"

    # 3. Manager Marcus (Alice's manager) approves the leave
    res_approve = client.put(
        f"/api/v1/leaves/{leave_id}/status",
        json={"status": "approved"},
        headers=manager_headers
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"
    assert res_approve.json()["approved_by"] == seeded_data["manager"].id


def test_manager_cannot_approve_non_report_or_self(client, manager_headers, other_manager_headers, bob_headers, seeded_data):
    today = date.today()

    # Bob (reports to other_manager) applies for leave
    bob_leave = client.post(
        "/api/v1/leaves",
        json={
            "leave_type": "sick",
            "start_date": str(today + timedelta(days=30)),
            "end_date": str(today + timedelta(days=31)),
            "reason": "Doctor appointment",
        },
        headers=bob_headers
    ).json()

    # Manager Marcus tries to approve Bob's leave -> 403 Forbidden
    res_mgr_bob = client.put(
        f"/api/v1/leaves/{bob_leave['id']}/status",
        json={"status": "approved"},
        headers=manager_headers
    )
    assert res_mgr_bob.status_code == 403

    # Manager Marcus applies for leave himself
    mgr_leave = client.post(
        "/api/v1/leaves",
        json={
            "leave_type": "annual",
            "start_date": str(today + timedelta(days=40)),
            "end_date": str(today + timedelta(days=42)),
            "reason": "Conference travel",
        },
        headers=manager_headers
    ).json()

    # Manager Marcus tries to approve his own leave -> 403 Forbidden
    res_self_approve = client.put(
        f"/api/v1/leaves/{mgr_leave['id']}/status",
        json={"status": "approved"},
        headers=manager_headers
    )
    assert res_self_approve.status_code == 403


def test_leave_balances_calculation(client, employee_headers, manager_headers):
    today = date.today()
    # Check initial balance
    res_init = client.get("/api/v1/leaves/balances", headers=employee_headers)
    assert res_init.status_code == 200
    balances = {b["leave_type"]: b for b in res_init.json()["balances"]}
    assert balances["annual"]["total_allowance"] == 15
    assert balances["annual"]["used_days"] == 0
    assert balances["annual"]["remaining_days"] == 15

    # Apply 5 days annual leave
    leave_res = client.post(
        "/api/v1/leaves",
        json={
            "leave_type": "annual",
            "start_date": str(today + timedelta(days=50)),
            "end_date": str(today + timedelta(days=54)),
            "reason": "Family vacation",
        },
        headers=employee_headers
    ).json()

    # Approve it
    client.put(
        f"/api/v1/leaves/{leave_res['id']}/status",
        json={"status": "approved"},
        headers=manager_headers
    )

    # Check updated balance
    res_after = client.get("/api/v1/leaves/balances", headers=employee_headers)
    assert res_after.status_code == 200
    balances_after = {b["leave_type"]: b for b in res_after.json()["balances"]}
    assert balances_after["annual"]["used_days"] == 5
    assert balances_after["annual"]["remaining_days"] == 10
