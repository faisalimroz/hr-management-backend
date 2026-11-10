def test_check_in_and_check_out_workflow(client, employee_headers):
    # 1. Check in
    checkin_payload = {"status": "present", "notes": "Starting morning standup"}
    res_in = client.post("/api/v1/attendance/check-in", json=checkin_payload, headers=employee_headers)
    assert res_in.status_code == 201
    in_data = res_in.json()
    assert in_data["status"] == "present"
    assert in_data["check_in_time"] is not None
    assert in_data["check_out_time"] is None

    # 2. Duplicate check in on same day -> 400
    res_in_dup = client.post("/api/v1/attendance/check-in", json=checkin_payload, headers=employee_headers)
    assert res_in_dup.status_code == 400
    assert "already checked in" in res_in_dup.json()["error"]["message"].lower()

    # 3. Check out
    checkout_payload = {"notes": "Wrapping up sprint work"}
    res_out = client.post("/api/v1/attendance/check-out", json=checkout_payload, headers=employee_headers)
    assert res_out.status_code == 200
    out_data = res_out.json()
    assert out_data["check_out_time"] is not None

    # 4. Duplicate check out on same day -> 400
    res_out_dup = client.post("/api/v1/attendance/check-out", json=checkout_payload, headers=employee_headers)
    assert res_out_dup.status_code == 400
    assert "already checked out" in res_out_dup.json()["error"]["message"].lower()


def test_check_out_without_check_in(client, other_manager_headers):
    res_out = client.post("/api/v1/attendance/check-out", json={}, headers=other_manager_headers)
    assert res_out.status_code == 400
    assert "without checking in first" in res_out.json()["error"]["message"].lower()


def test_attendance_logs_rbac(client, admin_headers, manager_headers, employee_headers, seeded_data):
    # Alice checks in
    client.post("/api/v1/attendance/check-in", json={"status": "present"}, headers=employee_headers)

    alice_id = seeded_data["employee"].id
    bob_id = seeded_data["bob"].id

    # Alice views own logs -> 200
    res_alice_own = client.get("/api/v1/attendance/logs", headers=employee_headers)
    assert res_alice_own.status_code == 200
    assert res_alice_own.json()["total"] >= 1

    # Alice tries to view Bob's logs -> 403 Forbidden
    res_alice_bob = client.get(f"/api/v1/attendance/logs?user_id={bob_id}", headers=employee_headers)
    assert res_alice_bob.status_code == 403

    # Manager Marcus views Alice's logs (direct report) -> 200
    res_mgr_alice = client.get(f"/api/v1/attendance/logs?user_id={alice_id}", headers=manager_headers)
    assert res_mgr_alice.status_code == 200

    # Manager Marcus tries to view Bob's logs (not direct report) -> 403
    res_mgr_bob = client.get(f"/api/v1/attendance/logs?user_id={bob_id}", headers=manager_headers)
    assert res_mgr_bob.status_code == 403

    # Admin views any logs -> 200
    res_admin_alice = client.get(f"/api/v1/attendance/logs?user_id={alice_id}", headers=admin_headers)
    assert res_admin_alice.status_code == 200
