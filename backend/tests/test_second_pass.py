"""Second review pass: risk history across follow-ups, evidence gaps in financial status,
accessory pricing and no price-only recycling."""

import json

from conftest import HEADERS, photo_bytes
from test_review_fixes import SALES, SCREEN, follow, obs, option, rec, snapshot

from app.schemas.functional import CheckResponse
from app.schemas.physical import ObservationReview
from app.services import functional_checks as fc
from app.services.recommendations import derive_repair_scenarios, recommend, repair_cost

DAMAGE = obs("obs-1", "physical_damage", "Back panel", views=("back",))
SWELLING = obs("ignored", "suspected_safety_risk", "Back panel lifting", views=("back",), risk="swelling")
COSMETIC = obs("ignored", "cosmetic_wear", "Back panel scratches", views=("back",))


def review(*history, response="disagree"):
    return [ObservationReview(observation_id="obs-1", response=response, follow_ups=list(history))]


# ---- 1. Risk history across several follow-ups ----


def test_damage_then_risk_then_unresolved_stays_blocked():
    reviews = review(follow("obs-1", "revised", 1, SWELLING), follow("obs-1", "unresolved", 1))
    state = fc.safety_state([DAMAGE], reviews)
    assert state.blocked
    assert state.risks[0].observation_id == "obs-1"
    assert state.risks[0].status == "identified_in_follow_up"
    assert fc.resolve_observations([DAMAGE], reviews)[0].observation.kind == "suspected_safety_risk"


def test_damage_then_risk_then_revised_to_cosmetic_stays_blocked():
    reviews = review(follow("obs-1", "revised", 1, SWELLING), follow("obs-1", "revised", 2, COSMETIC))
    state = fc.safety_state([DAMAGE], reviews)
    assert state.blocked
    assert state.risks[0].status == "unresolved"
    assert state.risks[0].part == "Back panel lifting"  # the risk evidence is still named


def test_identified_risk_cleared_by_explicit_not_supported_with_new_photos():
    reviews = review(follow("obs-1", "revised", 1, SWELLING), follow("obs-1", "not_supported", 2))
    state = fc.safety_state([DAMAGE], reviews)
    assert not state.blocked
    assert state.risks[0].status == "cleared_after_follow_up"


def test_clearance_without_new_photos_or_followed_by_other_results_does_not_clear():
    no_photos = review(follow("obs-1", "revised", 1, SWELLING), follow("obs-1", "not_supported", 0))
    later_unresolved = review(follow("obs-1", "revised", 1, SWELLING), follow("obs-1", "not_supported", 2),
                              follow("obs-1", "unresolved", 1))
    risk_again = review(follow("obs-1", "not_supported", 1), follow("obs-1", "revised", 1, SWELLING))
    for reviews in (no_photos, later_unresolved, risk_again):
        assert fc.safety_state([DAMAGE], reviews).blocked


def test_plan_endpoint_uses_full_history(client):
    body = {
        "device_type": "mobile",
        "observations": [DAMAGE.model_dump()],
        "reviews": [r.model_dump() for r in review(follow("obs-1", "revised", 1, SWELLING), follow("obs-1", "unresolved", 1))],
    }
    r = client.post("/api/checks/plan", json=body)
    assert r.status_code == 200 and r.json()["safety"]["blocked"] is True


def test_follow_up_endpoint_receives_prior_risk_context(client):
    prior = [follow("obs-1", "revised", 1, SWELLING).model_dump(mode="json")]
    effective = SWELLING.model_copy(update={"id": "obs-1"})
    r = client.post(
        "/api/assessments/follow-up",
        data={"device_type": "mobile", "observation": effective.model_dump_json(), "response": "disagree",
              "views": ["back", "followup"], "history": json.dumps(prior)},
        files=[("files", (f"p{i}.jpg", photo_bytes(), "image/jpeg")) for i in range(2)],
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["outcome"] == "unresolved"  # mock never clears a known risk
    assert r.json()["observation_id"] == "obs-1"


def test_follow_up_endpoint_rejects_invalid_history(client):
    r = client.post(
        "/api/assessments/follow-up",
        data={"device_type": "mobile", "observation": DAMAGE.model_dump_json(), "response": "disagree",
              "history": "not json"},
        headers=HEADERS,
    )
    assert r.status_code == 422


# ---- 2. Evidence gaps keep financial status conditional ----

RECORDS = SALES + [rec("repair_quote", 1000, 1200, scenario="front_glass_or_screen")]


def statuses(result):
    return {a: option(result, a).financial_status for a in ("resell_as_is", "repair_then_resell")}


def test_no_functional_results_keep_financials_conditional():
    result = recommend(snapshot([SCREEN], RECORDS, answers=None))
    assert statuses(result) == {"resell_as_is": "conditional", "repair_then_resell": "conditional"}
    assert result.financial_ranking.order == []
    assert set(result.financial_ranking.conditional) == {"resell_as_is", "repair_then_resell"}
    assert not result.financial_ranking.complete
    assert "no functional checks were recorded" in option(result, "repair_then_resell").financial_note
    assert "does not prove the device will work" in option(result, "repair_then_resell").financial_note


def test_partial_functional_results_keep_financials_conditional():
    answers = [CheckResponse(check_id="power_on", answer="pass"), CheckResponse(check_id="touch", answer="unsure")]
    result = recommend(snapshot([SCREEN], RECORDS, answers=answers))
    assert set(statuses(result).values()) == {"conditional"}
    assert "unknown or unanswered" in option(result, "resell_as_is").financial_note


def test_contradictory_functional_results_keep_financials_conditional():
    answers = [CheckResponse(check_id=c.id, answer="pass") for c in fc.CHECKS["mobile"]]
    answers[2] = CheckResponse(check_id="display", answer="fail")  # display fail + touch pass
    result = recommend(snapshot([SCREEN], RECORDS, answers=answers))
    assert option(result, "resell_as_is").financial_status == "conditional"
    assert option(result, "repair_then_resell").financial_status != "complete"  # display repair is also unpriced
    assert result.financial_ranking.order == []
    assert "contradict" in option(result, "resell_as_is").financial_note


def test_disputed_damage_keeps_financials_conditional():
    damage = obs("obs-9", "physical_damage", "Back panel", views=("back",))
    reviews = [ObservationReview(observation_id="obs-9", response="disagree")]
    result = recommend(snapshot([SCREEN, damage], RECORDS, reviews=reviews))
    assert option(result, "resell_as_is").financial_status == "conditional"


def test_fully_checked_device_with_confirmed_repair_is_complete():
    result = recommend(snapshot([SCREEN], RECORDS))
    assert statuses(result) == {"resell_as_is": "complete", "repair_then_resell": "complete"}
    assert result.financial_ranking.order == ["repair_then_resell", "resell_as_is"]
    assert result.financial_ranking.complete


def test_unconfirmed_alternative_fault_keeps_repair_conditional():
    answers = [CheckResponse(check_id=c.id, answer="fail" if c.id == "touch" else "pass") for c in fc.CHECKS["mobile"]]
    records = RECORDS + [rec("repair_quote", 3000, 3000, scenario="board_level")]
    result = recommend(snapshot([SCREEN], records, answers=answers))
    resell = option(result, "repair_then_resell")
    assert resell.repair_cost_complete  # every cause is priced...
    assert resell.financial_status == "conditional"  # ...but which one applies is not confirmed
    assert "is not confirmed" in resell.financial_note


# ---- 3. Charger / cable is never assumed free ----

QUOTES = [rec("repair_quote", 800, 1000, scenario="charging_port"), rec("repair_quote", 1500, 2000, scenario="battery"),
          rec("repair_quote", 3000, 4000, scenario="board_level")]


def test_priced_accessory_is_used_not_zero():
    scenarios = derive_repair_scenarios("mobile", [], ["charging"])
    est = repair_cost(scenarios, QUOTES + [rec("part_price", 500, 500, scenario="charger_accessory")], "THB")
    assert (est.cost.min, est.cost.max) == (500, 4000)
    assert est.complete  # an accessory purchase needs no labor


def test_missing_accessory_price_stays_unknown():
    est = repair_cost(derive_repair_scenarios("mobile", [], ["charging"]), QUOTES, "THB")
    assert est.cost.min == 800  # never a THB 0 lower bound
    assert not est.complete
    assert any("Replacement charger or cable" in n for n in est.notes)


def test_known_working_charger_rules_out_accessory_without_free_repair():
    answers = [CheckResponse(check_id=c.id, answer="fail" if c.id == "charging" else "pass",
                             accessory_check="known_working" if c.id == "charging" else None) for c in fc.CHECKS["mobile"]]
    snap = snapshot([], SALES + QUOTES, answers=answers)
    assert next(o for o in snap.functional.outcomes if o.check_id == "charging").accessory_check == "known_working"
    scenarios = derive_repair_scenarios("mobile", [], ["charging"], accessory_ruled_out=True)
    assert "charger_accessory" not in {s.id for s in scenarios}
    result = recommend(snap)
    resell = option(result, "repair_then_resell")
    assert resell.repair_cost.min == 800 and resell.repair_cost_complete
    assert not any("Before buying anything" in p for p in resell.prerequisites)


def test_unverified_charger_gets_explicit_no_cost_check_prerequisite():
    answers = [CheckResponse(check_id=c.id, answer="fail" if c.id == "charging" else "pass") for c in fc.CHECKS["mobile"]]
    result = recommend(snapshot([], SALES + QUOTES, answers=answers))
    resell = option(result, "repair_then_resell")
    assert any("Before buying anything, test with a charger and cable you know work" in p for p in resell.prerequisites)
    assert resell.repair_cost.min > 0
