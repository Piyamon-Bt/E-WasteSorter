from conftest import HEADERS, photo_bytes, upload


def test_missing_required_views_block_analysis(client):
    data, files = upload("mobile", views=["front", "back", "left", "right"])
    r = client.post("/api/assessments/physical", data=data, files=files, headers=HEADERS)
    assert r.status_code == 422
    problems = r.json()["detail"]["slot_problems"]
    assert "Missing required view: Top edge." in problems
    assert "Missing required view: Bottom edge." in problems


def test_duplicate_slot_is_rejected(client):
    data, files = upload("laptop", views=["screen", "screen", "keyboard", "lid", "underside", "left", "right"])
    r = client.post("/api/assessments/physical", data=data, files=files, headers=HEADERS)
    assert r.status_code == 422
    assert any("Assign only one photo" in p for p in r.json()["detail"]["slot_problems"])


def test_unusable_images_request_replacement(client):
    data, files = upload("mobile")
    files[0] = ("files", ("front.jpg", photo_bytes(size=(200, 150)), "image/jpeg"))  # too small
    files[1] = ("files", ("back.jpg", photo_bytes(color=(3, 3, 3), detail=False), "image/jpeg"))  # too dark
    files[2] = ("files", ("left.jpg", b"not an image", "image/jpeg"))
    r = client.post("/api/assessments/physical", data=data, files=files, headers=HEADERS)
    assert r.status_code == 422
    issues = {i["view"]: i["problem"] for i in r.json()["detail"]["image_issues"]}
    assert "too small" in issues["front"]
    assert "too dark" in issues["back"]
    assert "could not be read" in issues["left"]


def test_extra_detail_photos_are_allowed(client):
    data, files = upload("mobile", views=["front", "back", "left", "right", "top", "bottom", "detail", "detail"])
    r = client.post("/api/assessments/physical", data=data, files=files, headers=HEADERS)
    assert r.status_code == 200


def test_mock_result_is_labelled_and_keeps_one_view_damage(client):
    data, files = upload("mobile")
    r = client.post(
        "/api/assessments/physical", data=data, files=files, headers={**HEADERS, "X-Mock-Scenario": "visible_damage"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "simulated"
    assert "not analyzed" in body["summary"]
    damage = [o for o in body["observations"] if o["kind"] == "physical_damage"]
    assert damage and damage[0]["views"] == ["front"]
    assert body["view_check"] == "slot_assignment_only"


def test_assessment_id_header_required(client):
    data, files = upload("mobile")
    r = client.post("/api/assessments/physical", data=data, files=files)
    assert r.status_code == 422


def test_follow_up_disagreement_does_not_clear_mock_risk(client):
    data, files = upload("mobile")
    phys = client.post(
        "/api/assessments/physical", data=data, files=files, headers={**HEADERS, "X-Mock-Scenario": "suspected_risk"}
    ).json()
    risk = next(o for o in phys["observations"] if o["kind"] == "suspected_safety_risk")
    import json

    r = client.post(
        "/api/assessments/follow-up",
        data={"device_type": "mobile", "observation": json.dumps(risk), "response": "disagree", "note": "It is a case", "views": ["followup"]},
        files=[("files", ("close.jpg", photo_bytes(), "image/jpeg"))],
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["outcome"] == "unresolved"
