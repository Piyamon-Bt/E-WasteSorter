from datetime import datetime, timezone

from conftest import HEADERS

from app.providers import mock_provider
from app.schemas.functional import CheckResponse
from app.schemas.market import ConfirmedIdentity, PriceRecord, PriceRequest, ServicesRequest
from app.schemas.recommendation import AssessmentSnapshot, LocationChoice
from app.services import functional_checks as fc
from app.services import local_services, price_research, recommendations, report_export
from app.services.recommendations import derive_repair_scenarios, repair_cost

VIEWS = ["front", "back", "left", "right", "top", "bottom"]
KNOWN = ConfirmedIdentity(status="candidate_selected", brand="Examplephone", model="X12 (simulated)")
UNKNOWN = ConfirmedIdentity(status="unknown")


def snapshot(settings, scenario="visible_damage", answers="all_pass", identity=KNOWN, country="TH"):
    phys = mock_provider.assess_physical("mobile", VIEWS, scenario)
    if answers == "all_pass":
        responses = [CheckResponse(check_id=c.id, answer="pass") for c in fc.CHECKS["mobile"]]
    else:
        responses = answers
    functional = fc.evaluate("mobile", phys.observations, [], responses)
    damaged = [o.part for o in phys.observations if o.kind == "physical_damage"]
    failed = [o.check_id for o in functional.outcomes if o.status == "fail"]
    req = PriceRequest(device_type="mobile", identity=identity, country=country, damaged_parts=damaged, failed_checks=failed)
    prices = price_research.research(settings, "a" * 16, req, scenario)
    services = local_services.find(settings, "a" * 16, ServicesRequest(device_type="mobile", country=country, area="Bangkok"), scenario)
    return AssessmentSnapshot(device_type="mobile", physical=phys, functional=functional, identity=identity,
                              location=LocationChoice(country=country, area="Bangkok"), prices=prices, services=services)


def record(price_type, lo, hi, scenario_id=None, state="not_applicable", quality="unknown"):
    return PriceRecord(price_type=price_type, item="x", amount_min=lo, amount_max=hi, currency="THB", market="TH",
                       device_state=state, part_quality=quality, scenario_id=scenario_id, source_url="https://example.com/x",
                       source_title="t", retrieved_at=datetime.now(timezone.utc), match_level="close",
                       matching_conditions="", limitations="", simulated=True)


def test_unknown_model_skips_prices_but_keeps_services(configure):
    snap = snapshot(configure(), identity=UNKNOWN)
    assert snap.prices.status == "skipped_unknown_identity"
    assert snap.prices.records == []
    assert snap.services.services
    rec = recommendations.recommend(snap)
    assert not rec.financial_ranking.complete
    assert any("Model unknown" in f for f in rec.conditional_findings)


def test_selected_unverified_model_is_conditional(configure):
    rec = recommendations.recommend(snapshot(configure()))
    assert any("not verified" in f for f in rec.conditional_findings)


def test_no_local_prices_still_reports_without_foreign_substitution(configure):
    snap = snapshot(configure(), country="US")  # no simulated data for US
    assert snap.prices.status == "insufficient_data"
    assert snap.prices.records == []
    assert any("not substituted" in n for n in snap.prices.notes)
    text = report_export.build_report(snap, recommendations.recommend(snap))
    assert "Insufficient data" in text


def test_missing_market_data_scenario(configure):
    snap = snapshot(configure(), scenario="missing_market_data")
    assert snap.prices.records == [] and snap.prices.status == "insufficient_data"


def test_provider_failure_returns_partial_results(configure):
    snap = snapshot(configure(), scenario="provider_failure")
    assert snap.prices.status == "failed" and snap.prices.issues[0].code == "timeout"
    assert snap.services.issues[0].code == "quota"
    rec = recommendations.recommend(snap)
    assert rec.options  # still a supported assessment, not blocked
    assert rec.financial_ranking.order == []


def test_one_view_damage_leads_to_repair_options(configure):
    rec = recommendations.recommend(snapshot(configure(), scenario="visible_damage"))
    actions = [o.action for o in rec.options]
    assert "repair_then_reuse" in actions and "repair_then_resell" in actions


def test_cosmetic_only_does_not_recommend_repair(configure):
    rec = recommendations.recommend(snapshot(configure(), scenario="normal"))
    actions = [o.action for o in rec.options]
    assert "repair_then_reuse" not in actions and "repair_then_resell" not in actions
    assert any("Cosmetic wear alone" in f for f in rec.conditional_findings)


def test_safety_risk_constrains_options(configure):
    snap = snapshot(configure(), scenario="suspected_risk", answers=[])
    rec = recommendations.recommend(snap)
    actions = [o.action for o in rec.options]
    assert rec.safety_constrained
    assert "reuse" not in actions and "resell_as_is" not in actions
    assert "recycle" in actions


def test_power_failure_alone_does_not_force_recycling(configure):
    answers = [CheckResponse(check_id="power_on", answer="fail")]
    rec = recommendations.recommend(snapshot(configure(), scenario="normal", answers=answers))
    actions = [o.action for o in rec.options]
    assert "repair_then_reuse" in actions and "resell_as_is" in actions
    assert rec.resource_ranking.order[-1] == "recycle"


def test_financial_arithmetic_and_no_double_counted_labor():
    scenarios = derive_repair_scenarios("mobile", ["Front glass"], [])
    records = [
        record("repair_quote", 1800, 2400, "front_glass_or_screen", quality="aftermarket"),
        record("part_price", 2800, 3200, "front_glass_or_screen", quality="genuine"),
        record("repair_labor", 500, 800, "front_glass_or_screen"),
    ]
    cost, notes = repair_cost(scenarios, records, "THB")
    # The combined quote is used; part + labor are not added on top of it.
    assert (cost.min, cost.max) == (1800, 2400)
    parts_only, _ = repair_cost(scenarios, records[1:], "THB")
    assert (parts_only.min, parts_only.max) == (3300, 4000)


def test_net_proceeds_are_gross_minus_repair_cost(configure):
    rec = recommendations.recommend(snapshot(configure(), scenario="visible_damage"))
    opt = next(o for o in rec.options if o.action == "repair_then_resell")
    assert opt.net_proceeds.min == opt.gross_sale.min - opt.repair_cost.max
    assert opt.net_proceeds.max == opt.gross_sale.max - opt.repair_cost.min
    reuse = next(o for o in rec.options if o.action == "reuse")
    assert reuse.net_proceeds is None and reuse.avoided_cost is not None


def test_charging_symptom_gives_alternative_scenarios():
    scenarios = derive_repair_scenarios("mobile", [], ["charging"])
    assert len(scenarios) >= 3
    assert len({s.need for s in scenarios}) == 1


def test_rankings_can_differ_and_explain(configure):
    rec = recommendations.recommend(snapshot(configure(), scenario="visible_damage"))
    assert rec.resource_ranking.order[0] == "reuse"
    # Financial ranking covers cash outcomes only; reuse is explained separately.
    assert rec.financial_ranking.order[0] == "repair_then_resell"
    assert "reuse" not in rec.financial_ranking.order
    assert any("earns no cash" in e for e in rec.financial_ranking.explanation)
    assert rec.rankings_differ and "no universal" in rec.rankings_differ.lower()
    assert any("No environmental savings are quantified" in e for e in rec.resource_ranking.explanation)


def test_location_denied_manual_area_works_and_distance_only_with_coords(configure):
    settings = configure()
    manual = local_services.find(settings, "a" * 16, ServicesRequest(device_type="laptop", country="TH", area="Chiang Mai"), "normal")
    assert manual.services and all(s.distance_km is None for s in manual.services)
    coords = local_services.find(settings, "a" * 16, ServicesRequest(device_type="laptop", country="TH", latitude=13.75, longitude=100.5), "normal")
    assert all(s.distance_kind == "straight_line" for s in coords.services)
    neither = local_services.find(settings, "a" * 16, ServicesRequest(device_type="laptop", country="TH"), "normal")
    assert neither.services == [] and "Enter an area" in neither.notes[0]


def test_report_is_traceable_and_labelled(configure):
    snap = snapshot(configure(), scenario="visible_damage")
    text = report_export.build_report(snap, recommendations.recommend(snap))
    assert "DEMO MODE — SIMULATED RESULTS" in text
    assert "https://example.com/simulated/" in text
    assert "THB" in text and "Retrieved" in text
    assert "user-reported" in text


def test_recommendation_and_report_endpoints(client, configure):
    snap = snapshot(configure(), scenario="visible_damage")
    body = snap.model_dump(mode="json")
    r = client.post("/api/recommendations", json=body)
    assert r.status_code == 200
    rep = client.post("/api/report", json={"snapshot": body, "recommendation": r.json()})
    assert rep.status_code == 200
    assert rep.headers["content-type"].startswith("text/markdown")
    assert "attachment" in rep.headers["content-disposition"]


def test_price_endpoint(client):
    r = client.post("/api/market/prices", headers=HEADERS, json={"device_type": "laptop", "identity": {"status": "confirmed", "brand": "Examplebook", "model": "Air 14"}, "country": "th", "damaged_parts": ["Left hinge cover"]})
    assert r.status_code == 200
    body = r.json()
    assert body["country"] == "TH"
    assert all(rec["simulated"] for rec in body["records"])
