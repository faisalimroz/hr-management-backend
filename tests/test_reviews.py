def test_performance_review_submission(client, manager_headers, employee_headers, seeded_data):
    alice_id = seeded_data["employee"].id
    review_data = {
        "employee_id": alice_id,
        "review_period": "Q1 2026",
        "rating": 5,
        "feedback": "Outstanding performance in system modularization.",
        "goals": "Architect distributed event caching mechanism."
    }
    # Manager submits review for direct report Alice -> 201
    res = client.post("/api/v1/reviews", json=review_data, headers=manager_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["rating"] == 5
    assert data["employee_id"] == alice_id
    assert data["reviewer_id"] == seeded_data["manager"].id

    # Alice views her own reviews -> 200
    res_emp = client.get(f"/api/v1/reviews/{alice_id}", headers=employee_headers)
    assert res_emp.status_code == 200
    reviews = res_emp.json()
    assert len(reviews) >= 1
    assert reviews[0]["rating"] == 5


def test_performance_review_forbidden_cases(client, manager_headers, employee_headers, seeded_data):
    bob_id = seeded_data["bob"].id
    mgr_id = seeded_data["manager"].id

    # 1. Manager attempts to review Bob (who reports to other_manager) -> 403
    res_mgr_bob = client.post(
        "/api/v1/reviews",
        json={
            "employee_id": bob_id,
            "review_period": "Q1 2026",
            "rating": 4,
            "feedback": "Good work on frontend tasks."
        },
        headers=manager_headers
    )
    assert res_mgr_bob.status_code == 403

    # 2. Employee attempts to submit review -> 403
    res_emp_review = client.post(
        "/api/v1/reviews",
        json={
            "employee_id": bob_id,
            "review_period": "Q1 2026",
            "rating": 4,
            "feedback": "Peer review"
        },
        headers=employee_headers
    )
    assert res_emp_review.status_code == 403

    # 3. Manager tries to review oneself -> 400
    res_self = client.post(
        "/api/v1/reviews",
        json={
            "employee_id": mgr_id,
            "review_period": "Q1 2026",
            "rating": 5,
            "feedback": "Self evaluation"
        },
        headers=manager_headers
    )
    assert res_self.status_code == 400
