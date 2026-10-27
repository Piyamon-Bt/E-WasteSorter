"""Regression tests for the code-review fixes: safety after follow-up, shared repairs,
separate sale channels, gated recycling and follow-up upload limits."""

import json
from datetime import datetime, timezone

from conftest import HEADERS, photo_bytes

from app.providers import openai_provider
from app.schemas.functional import CheckResponse
from app.schemas.market import ConfirmedIdentity, PriceRecord, PriceResearch
from app.schemas.physical import (
    FollowUpResult,
    IdentitySuggestion,
    Observation,
    ObservationReview,
    PhysicalAssessment,
)
from app.schemas.recommendation import AssessmentSnapshot
from app.services import functional_checks as fc
from app.services import image_assessment
from app.services.recommendations import derive_repair_scenarios, recommend, repair_cost

NOW = datetime.now(timezone.utc)
IDENTITY = ConfirmedIdentity(status="confirmed", brand="Brand", model="Model")


def obs(id, kind, part, views=("front",), risk=None):
    return Observation(id=id, kind=kind, part=part, description=part, views=list(views), visible_evidence="",
                       uncertainty="medium", uncertainty_reason="", risk_type=risk)


def follow(obs_id, outcome, extra, revised=None):
    return FollowUpResult(observation_id=obs_id, outcome=outcome, revised_observation=revised, explanation="",
                          extra_images=extra, source="simulated", model=None)


def rec(price_type, lo, hi, state="not_applicable", scenario=None, quality="not_applicable", match="close"):
    return PriceRecord(price_type=price_type, item="x", amount_min=lo, amount_max=hi, currency="THB", market="TH",
                       device_state=state, part_quality=quality, scenario_id=scenario,
                       source_url="https://example.com/x", source_title="t", retrieved_at=NOW, match_level=match,
                       matching_conditions="", limitations="", simulated=True)


def snapshot(observations, records, answers="all_pass", reviews=()):
    physical = PhysicalAssessment(
        source="simulated", model=None, device_type="mobile", observations=observations, unassessable_areas=[],
        identity=IdentitySuggestion(evidence_strength="none", candidates=[], visible_specs=[], notes=""), summary="",
    )
    responses = (
        [CheckResponse(check_id=c.id, answer="pass") for c in fc.CHECKS["mobile"]]
        if answers == "all_pass" else answers
    )
    functional = None if answers is None else fc.evaluate("mobile", observations, list(reviews), responses)
    prices = PriceResearch(source="simulated", model=None, country="TH", identity_label="Brand Model",
                           status="complete", retrieved_at=NOW, records=records, channels=[], repair_scenarios=[], issues=[])
    return AssessmentSnapshot(device_type="mobile", physical=physical, reviews=list(reviews), functional=functional,
                              identity=IDENTITY, prices=prices)


def option(result, action):
    return next((o for o in result.options if o.action == action), None)


SCREEN = obs("obs-1", "physical_damage", "Front glass")
BACK = obs("obs-2", "physical_damage", "Back panel", views=("back",))
SALES = [rec("buyback_offer", 6000, 7000, "working"), rec("buyback_offer", 2000, 2500, "damaged_or_faulty")]


# ---- 1. Safety evaluated on the effective observation ----


def test_ordinary_damage_revised_into_swelling_blocks_checks():
    revised = obs("other-id", "suspected_safety_risk", "Back panel lifting", views=("back",), risk="swelling")
    reviews = [ObservationReview(observation_id="obs-2", response="disagree", follow_ups=[follow("obs-2", "revised", 1, revised)])]
    state = fc.safety_state([BACK], reviews)
    assert state.blocked
    assert state.risks[0].status == "identified_in_follow_up"
    assert state.risks[0].observation_id == "obs-2"  # original id kept for provenance
    assert state.risks[0].part == "Back panel lifting"
    assert fc.build_plan("mobile", [BACK], reviews).checks == []
    assert fc.resolve_observations([BACK], reviews)[0].observation.id == "obs-2"


def test_original_risk_stays_blocked_unless_explicitly_cleared_with_new_photos():
    risk = obs("obs-3", "suspected_safety_risk", "Battery area", views=("back",), risk="swelling")
    cosmetic = obs("x", "cosmetic_wear", "Back panel", views=("back",))
    not_clearing = [
        ObservationReview(observation_id="obs-3", response="disagree"),
        ObservationReview(observation_id="obs-3", response="disagree", follow_ups=[follow("obs-3", "unresolved", 2)]),
        ObservationReview(observation_id="obs-3", response="disagree", follow_ups=[follow("obs-3", "upheld", 2)]),
        ObservationReview(observation_id="obs-3", response="disagree", follow_ups=[follow("obs-3", "not_supported", 0)]),
        # A revision away from the risk kind is not an explicit "not present" result.
        ObservationReview(observation_id="obs-3", response="disagree", follow_ups=[follow("obs-3", "revised", 2, cosmetic)]),
    ]
    for review in not_clearing:
        state = fc.safety_state([risk], [review])
        assert state.blocked, review
        assert state.risks[0].status == "unresolved"


def test_valid_risk_clearance_needs_new_photos_and_not_supported_outcome():
    risk = obs("obs-3", "suspected_safety_risk", "Battery area", views=("back",), risk="swelling")
    reviews = [ObservationReview(observation_id="obs-3", response="disagree", follow_ups=[follow("obs-3", "not_supported", 1)])]
    state = fc.safety_state([risk], reviews)
    assert not state.blocked
    assert state.risks[0].status == "cleared_after_follow_up"
    assert fc.build_plan("mobile", [risk], reviews).checks


# ---- 2. Shared and distinct repairs ----


def test_shared_screen_repair_is_charged_once():
    scenarios = derive_repair_scenarios("mobile", ["Front glass"], ["touch"])
    screen = next(s for s in scenarios if s.id == "front_glass_or_screen")
    assert len(screen.needs) == 2
    est = repair_cost(scenarios, [rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen")], "THB")
    assert est.cost.min == 1000 and est.cost.max == 1000  # not 2,000
    # The touch fault may have another cause (board) without a price, so the cost is not complete.
    assert not est.complete
    assert any("counted once" in n for n in est.notes)
    assert any("could be higher" in n for n in est.notes)


def test_shared_repair_with_all_causes_priced_is_complete():
    scenarios = derive_repair_scenarios("mobile", ["Front glass"], ["touch"])
    records = [rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen"),
               rec("repair_quote", 3000, 3000, scenario="board_level")]
    est = repair_cost(scenarios, records, "THB")
    assert (est.cost.min, est.cost.max) == (1000, 4000)  # screen fixes both, or screen + board
    assert est.complete


def test_distinct_repairs_are_added():
    scenarios = derive_repair_scenarios("mobile", ["Front glass", "Back panel"], [])
    records = [rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen"),
               rec("repair_quote", 800, 800, scenario="back_panel")]
    est = repair_cost(scenarios, records, "THB")
    assert (est.cost.min, est.cost.max) == (1800, 1800)
    assert est.complete


def test_combined_quote_is_not_added_to_part_and_labor_of_same_quality():
    scenarios = derive_repair_scenarios("mobile", ["Front glass"], [])
    records = [rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen", quality="genuine"),
               rec("part_price", 700, 700, scenario="front_glass_or_screen", quality="genuine"),
               rec("repair_labor", 300, 300, scenario="front_glass_or_screen")]
    est = repair_cost(scenarios, records, "THB")
    assert (est.cost.min, est.cost.max) == (1000, 1000)


def test_missing_labor_is_partial_and_not_definitively_ranked():
    records = SALES + [rec("part_price", 700, 700, scenario="front_glass_or_screen", quality="genuine")]
    est = repair_cost(derive_repair_scenarios("mobile", ["Front glass"], []), records, "THB")
    assert est.cost.min == 700 and not est.complete
    assert any("labor not included" in n for n in est.notes)
    result = recommend(snapshot([SCREEN], records))
    resell = option(result, "repair_then_resell")
    assert resell.financial_status == "conditional" and not resell.repair_cost_complete
    assert "repair_then_resell" not in result.financial_ranking.order
    assert "repair_then_resell" in result.financial_ranking.conditional
    assert not result.financial_ranking.complete


def test_unpriced_alternative_causes_keep_comparison_conditional():
    answers = [CheckResponse(check_id=c.id, answer="fail" if c.id == "charging" else "pass") for c in fc.CHECKS["mobile"]]
    records = SALES + [rec("repair_quote", 1200, 1500, scenario="battery")]
    result = recommend(snapshot([], records, answers=answers))
    resell = option(result, "repair_then_resell")
    assert not resell.repair_cost_complete
    assert resell.financial_status == "conditional"
    assert any("No price evidence" in u for u in resell.uncertainty)


# ---- 3. Sale channels stay separate ----


def test_low_buyback_and_high_asking_price_are_not_merged():
    records = [rec("buyback_offer", 3000, 3500, "working"), rec("asking_price", 9000, 11000, "working"),
               rec("buyback_offer", 1000, 1500, "damaged_or_faulty"),
               rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen")]
    result = recommend(snapshot([SCREEN], records))
    resell = option(result, "repair_then_resell")
    channels = {(c.price_type, c.range.min, c.range.max) for c in resell.sale_channels}
    assert ("buyback_offer", 3000, 3500) in channels and ("asking_price", 9000, 11000) in channels
    assert (resell.gross_sale.min, resell.gross_sale.max) == (3000, 3500)  # buyback basis, never 3,000–11,000
    assert resell.sale_basis == "buyback_offer"
    assert (resell.net_proceeds.min, resell.net_proceeds.max) == (2000, 2500)
    assert resell.financial_status == "complete"
    assert sum(c.used_for_calculation for c in resell.sale_channels) == 1


def test_asking_price_basis_is_conditional():
    records = [rec("asking_price", 9000, 11000, "working"), rec("asking_price", 4000, 5000, "damaged_or_faulty"),
               rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen")]
    result = recommend(snapshot([SCREEN], records))
    assert option(result, "resell_as_is").financial_status == "conditional"
    assert "not verified sale proceeds" in option(result, "resell_as_is").financial_note
    assert result.financial_ranking.order == []
    assert set(result.financial_ranking.conditional) == {"resell_as_is", "repair_then_resell"}


def test_options_on_different_channels_are_conditional():
    records = [rec("asking_price", 9000, 11000, "working"), rec("buyback_offer", 1000, 1500, "damaged_or_faulty"),
               rec("repair_quote", 1000, 1000, scenario="front_glass_or_screen")]
    result = recommend(snapshot([SCREEN], records))
    assert option(result, "resell_as_is").financial_status == "conditional"
    assert any("could not be compared on one basis" in e for e in result.financial_ranking.explanation)


def test_indicative_records_are_not_used_in_calculation():
    records = [rec("buyback_offer", 50000, 60000, "working", match="indicative")] + SALES
    result = recommend(snapshot([], records))
    assert (option(result, "resell_as_is").gross_sale.max) == 7000


# ---- 4. Recycle only when supported ----


def test_normal_working_device_has_no_recycle_option():
    result = recommend(snapshot([obs("c", "cosmetic_wear", "Back panel", views=("back",))], SALES))
    assert option(result, "recycle") is None
    assert "recycle" not in result.resource_ranking.order
    assert result.disposal_guidance


def test_unknown_condition_has_no_recycle_and_no_merged_as_is_value():
    result = recommend(snapshot([], SALES, answers=None))
    assert option(result, "recycle") is None
    as_is = option(result, "resell_as_is")
    assert as_is.gross_sale is None and {c.device_state for c in as_is.sale_channels} == {"working", "damaged_or_faulty"}
    assert "resell_as_is" in result.financial_ranking.unranked


def test_power_failure_alone_does_not_offer_recycle():
    answers = [CheckResponse(check_id="power_on", answer="fail")]
    records = SALES + [rec("repair_quote", 1500, 2000, scenario="battery")]
    result = recommend(snapshot([], records, answers=answers))
    assert option(result, "recycle") is None
    assert option(result, "repair_then_reuse") is not None


def test_uneconomic_repair_is_a_finding_not_a_recycle_recommendation():
    records = SALES + [rec("repair_quote", 9000, 12000, scenario="front_glass_or_screen")]
    result = recommend(snapshot([SCREEN], records))
    assert option(result, "recycle") is None
    assert "recycle" not in result.resource_ranking.order + result.financial_ranking.order + result.financial_ranking.unranked
    assert any("may not be financially worthwhile" in f for f in result.conditional_findings)
    # Other paths stay available; price evidence alone does not mean end of life.
    assert option(result, "reuse") is not None and option(result, "resell_as_is") is not None
    assert result.disposal_guidance


# ---- 5. Follow-up upload limits ----


def _follow_up_request(client, n_files, data=None):
    risk = obs("obs-1", "physical_damage", "Front glass")
    return client.post(
        "/api/assessments/follow-up",
        data={"device_type": "mobile", "observation": risk.model_dump_json(), "response": "disagree",
              "views": ["front"] + ["followup"] * (n_files - 1)},
        files=[("files", (f"p{i}.jpg", data or photo_bytes(), "image/jpeg")) for i in range(n_files)],
        headers=HEADERS,
    )


def test_over_limit_follow_up_makes_no_provider_call(configure, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    configure(app_mode="live", openai_api_key="sk-test", max_images_per_request=3)
    calls = {"provider": 0, "processing": 0}
    monkeypatch.setattr(openai_provider, "create", lambda: calls.__setitem__("provider", calls["provider"] + 1))
    original_check = image_assessment.check_image
    monkeypatch.setattr(image_assessment, "check_image",
                        lambda *a: (calls.__setitem__("processing", calls["processing"] + 1), original_check(*a))[1])
    r = _follow_up_request(TestClient(app), 4)
    assert r.status_code == 422
    assert "at most 3" in r.json()["detail"]["message"]
    assert calls == {"provider": 0, "processing": 0}


def test_oversized_follow_up_file_is_rejected_before_processing(configure, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    configure(max_upload_mb=0.01)  # about 10 KB
    monkeypatch.setattr(image_assessment, "check_image", lambda *a: (_ for _ in ()).throw(AssertionError("processed")))
    r = _follow_up_request(TestClient(app), 1, data=b"\xff" * 20_000)
    assert r.status_code == 422
    assert "larger than" in r.json()["detail"]["message"]


def test_follow_up_within_limit_still_works(client):
    r = _follow_up_request(client, 2)
    assert r.status_code == 200
    assert json.loads(r.text)["observation_id"] == "obs-1"
