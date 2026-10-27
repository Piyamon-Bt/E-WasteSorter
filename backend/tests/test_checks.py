from app.providers import mock_provider
from app.schemas.functional import CheckResponse
from app.schemas.physical import FollowUpResult, ObservationReview
from app.services import functional_checks as fc

VIEWS_MOBILE = ["front", "back", "left", "right", "top", "bottom"]


def risk_assessment():
    return mock_provider.assess_physical("mobile", VIEWS_MOBILE, "suspected_risk")


def risk_id(phys):
    return next(o.id for o in phys.observations if o.kind == "suspected_safety_risk")


def follow(obs_id, outcome, extra):
    return FollowUpResult(observation_id=obs_id, outcome=outcome, revised_observation=None,
                          explanation="", extra_images=extra, source="simulated", model=None)


def test_risk_blocks_power_and_charging_checks():
    phys = risk_assessment()
    plan = fc.build_plan("mobile", phys.observations, [])
    assert plan.safety.blocked
    assert plan.checks == []
    assert any("Do not power on or charge" in g for g in plan.safety.guidance)


def test_disagreement_alone_keeps_risk_blocked():
    phys = risk_assessment()
    rid = risk_id(phys)
    reviews = [ObservationReview(observation_id=rid, response="disagree", note="It's just my case")]
    state = fc.safety_state(phys.observations, reviews)
    assert state.blocked
    assert state.risks[0].status == "unresolved"


def test_follow_up_without_new_photos_cannot_clear_risk():
    phys = risk_assessment()
    rid = risk_id(phys)
    reviews = [ObservationReview(observation_id=rid, response="disagree", follow_ups=[follow(rid, "not_supported", 0)])]
    assert fc.safety_state(phys.observations, reviews).blocked


def test_follow_up_with_new_photos_can_clear_risk():
    phys = risk_assessment()
    rid = risk_id(phys)
    reviews = [ObservationReview(observation_id=rid, response="disagree", follow_ups=[follow(rid, "not_supported", 2)])]
    state = fc.safety_state(phys.observations, reviews)
    assert not state.blocked
    assert state.risks[0].status == "cleared_after_follow_up"
    assert fc.build_plan("mobile", phys.observations, reviews).checks


def test_evaluation_under_risk_marks_everything_blocked():
    phys = risk_assessment()
    ev = fc.evaluate("mobile", phys.observations, [], [CheckResponse(check_id="power_on", answer="pass")])
    assert ev.blocked_by_safety
    assert all(o.status == "blocked_by_safety" for o in ev.outcomes)


def test_cracked_glass_and_working_touch_can_both_be_true():
    phys = mock_provider.assess_physical("mobile", VIEWS_MOBILE, "visible_damage")
    answers = [CheckResponse(check_id=c.id, answer="pass") for c in fc.CHECKS["mobile"]]
    ev = fc.evaluate("mobile", phys.observations, [], answers)
    assert ev.complete
    assert ev.clarifications == []
    assert any("Both are true" in f for f in ev.conditional_findings)


def test_unknown_and_unable_stay_unknown_not_pass():
    phys = mock_provider.assess_physical("mobile", VIEWS_MOBILE, "normal")
    answers = [
        CheckResponse(check_id="power_on", answer="pass"),
        CheckResponse(check_id="charging", answer="unable"),
        CheckResponse(check_id="display", answer="unsure"),
    ]
    ev = fc.evaluate("mobile", phys.observations, [], answers)
    status = {o.check_id: o.status for o in ev.outcomes}
    assert status["charging"] == "unable"
    assert status["display"] == "unsure"
    assert status["touch"] == "not_answered"
    assert not ev.complete
    assert any("not as working" in f for f in ev.conditional_findings)


def test_power_failure_makes_dependent_checks_unavailable():
    phys = mock_provider.assess_physical("laptop", ["screen", "keyboard", "lid", "underside", "left", "right"], "normal")
    answers = [CheckResponse(check_id="power_on", answer="fail"), CheckResponse(check_id="display", answer="pass")]
    ev = fc.evaluate("laptop", phys.observations, [], answers)
    status = {o.check_id: o.status for o in ev.outcomes}
    assert status["display"] == "unavailable_power_failed"
    assert status["charging"] == "not_answered"  # charging can still be checked without power
    assert ev.clarifications  # a Pass that needs power is questioned
    assert any("does not mean recycling" in f for f in ev.conditional_findings)


def test_conflicting_display_and_touch_ask_for_clarification():
    phys = mock_provider.assess_physical("mobile", VIEWS_MOBILE, "normal")
    answers = [CheckResponse(check_id="power_on", answer="pass"), CheckResponse(check_id="display", answer="fail"),
               CheckResponse(check_id="touch", answer="pass")]
    ev = fc.evaluate("mobile", phys.observations, [], answers)
    assert any("How did you confirm touch" in c for c in ev.clarifications)


def test_charging_failure_is_scenarios_not_diagnosis():
    phys = mock_provider.assess_physical("mobile", VIEWS_MOBILE, "normal")
    ev = fc.evaluate("mobile", phys.observations, [], [CheckResponse(check_id="charging", answer="fail")])
    assert any("not a confirmed part failure" in f for f in ev.conditional_findings)


def test_checks_api_endpoint(client):
    phys = risk_assessment()
    r = client.post("/api/checks/plan", json={"device_type": "mobile", "observations": [o.model_dump() for o in phys.observations], "reviews": []})
    assert r.status_code == 200
    assert r.json()["safety"]["blocked"] is True
