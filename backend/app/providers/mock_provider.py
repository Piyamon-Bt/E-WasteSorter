"""Mock provider: simulated results with the same schemas as the live providers.

It never calls a paid API and never inspects image contents.
"""

import math
from datetime import datetime, timezone

from ..fixtures import mock_data as fx
from ..schemas.market import (
    ChannelStatus,
    LocalService,
    PriceRecord,
    PriceRequest,
    PriceResearch,
    RepairScenario,
    ServicesRequest,
    ServicesResult,
)
from ..schemas.physical import (
    FollowUpResult,
    IdentitySuggestion,
    Observation,
    PhysicalAssessment,
)
from .errors import ProviderError

MOCK_MODEL = "mock-fixture"


def resolve_scenario(name: str | None) -> str:
    return name if name in fx.MOCK_SCENARIOS else fx.DEFAULT_SCENARIO


def assess_physical(device_type: str, views: list[str], scenario: str) -> PhysicalAssessment:
    raw = [fx.COSMETIC[device_type]]
    if scenario in ("visible_damage", "provider_failure", "unknown_model"):
        raw.append(fx.DAMAGE[device_type])
    if scenario == "suspected_risk":
        raw.append(fx.RISK[device_type])
    raw.append(
        {
            "kind": "unassessable",
            "part": "Internal components",
            "description": "Internal condition cannot be judged from external photos.",
            "views": [],
            "visible_evidence": "Not visible in external photos.",
            "uncertainty": "high",
            "uncertainty_reason": "External photos only.",
            "risk_type": None,
        }
    )
    observations = [
        Observation(id=f"obs-{i + 1}", **{**o, "views": [v for v in o["views"] if v in views]})
        for i, o in enumerate(raw)
    ]
    identity = fx.IDENTITY_UNKNOWN if scenario == "unknown_model" else fx.IDENTITY_KNOWN[device_type]
    return PhysicalAssessment(
        source="simulated",
        model=MOCK_MODEL,
        device_type=device_type,
        observations=observations,
        unassessable_areas=fx.UNASSESSABLE[device_type],
        identity=IdentitySuggestion(**identity),
        summary=f"Simulated result for scenario: {fx.MOCK_SCENARIOS[scenario]}. Your photos were not analyzed.",
    )


def follow_up(observation: Observation, response: str, extra_images: int) -> FollowUpResult:
    """Simulated follow-up. A suspected risk always stays unresolved in mock mode."""
    if observation.kind == "suspected_safety_risk":
        outcome = "unresolved"
        explanation = (
            "Simulated review: the additional evidence does not rule out battery swelling. "
            "Disagreement alone does not clear a safety risk; professional inspection is still advised."
        )
    elif response == "disagree" and extra_images > 0:
        outcome = "not_supported"
        explanation = "Simulated review: the additional photos do not show the reported issue."
    else:
        outcome = "upheld" if response == "agree" else "unresolved"
        explanation = "Simulated review: no new evidence changes this observation."
    return FollowUpResult(
        observation_id=observation.id,
        outcome=outcome,
        revised_observation=None,
        explanation=explanation,
        extra_images=extra_images,
        source="simulated",
        model=MOCK_MODEL,
    )


def _record(price_type, item, amount, state, quality, scenario_id, country, currency, now, slug):
    return PriceRecord(
        price_type=price_type,
        item=item,
        amount_min=amount[0],
        amount_max=amount[1],
        currency=currency,
        market=country,
        device_state=state,
        part_quality=quality,
        scenario_id=scenario_id,
        source_url=f"https://example.com/simulated/{slug}",
        source_title="Simulated source (not real evidence)",
        retrieved_at=now,
        match_level="close",
        matching_conditions="Simulated match on device type and condition only.",
        limitations="Simulated fixture for demo purposes. Not a real listing, offer or quotation.",
        simulated=True,
    )


def research_prices(req: PriceRequest, scenarios: list[RepairScenario], scenario: str) -> PriceResearch:
    now = datetime.now(timezone.utc)
    if scenario == "provider_failure":
        raise ProviderError("timeout", "Simulated failure: the price search timed out.")
    base = PriceResearch(
        source="simulated",
        model=MOCK_MODEL,
        country=req.country,
        identity_label=req.identity.label(),
        status="insufficient_data",
        retrieved_at=now,
        records=[],
        channels=[],
        repair_scenarios=scenarios,
        issues=[],
    )
    currency = fx.MOCK_PRICE_COUNTRIES.get(req.country)
    if scenario == "missing_market_data" or currency is None:
        base.channels = [
            ChannelStatus(price_type=t, status="insufficient_data", note="No simulated local data for this market.")
            for t in ("asking_price", "buyback_offer", "repair_quote")
        ]
        base.notes.append("No local price evidence found. Prices from other countries are not substituted.")
        return base

    p = fx.PRICES[req.device_type]
    records: list[PriceRecord] = []

    def rec(price_type, item, amount, state, quality, scenario_id):
        slug = f"{req.device_type}-{len(records) + 1}"
        return _record(price_type, item, amount, state, quality, scenario_id, req.country, currency, now, slug)

    records.append(rec("asking_price", "Used, working, good condition", p["asking_working"], "working", "not_applicable", None))
    records.append(rec("asking_price", "Used, damaged or faulty", p["asking_damaged"], "damaged_or_faulty", "not_applicable", None))
    records.append(rec("buyback_offer", "Shop buyback, working", p["buyback_working"], "working", "not_applicable", None))
    records.append(rec("buyback_offer", "Shop buyback, damaged", p["buyback_damaged"], "damaged_or_faulty", "not_applicable", None))
    for s in scenarios:
        for price_type, quality, amount in p["quotes"].get(s.id, []):
            records.append(rec(price_type, s.title, amount, "not_applicable", quality, s.id))

    base.records = records
    base.status = "complete"
    found = {r.price_type for r in records}
    base.channels = [
        ChannelStatus(
            price_type=t,
            status="found" if t in found else "insufficient_data",
            note="Simulated." if t in found else "No simulated evidence for this channel.",
        )
        for t in ("asking_price", "completed_sale", "buyback_offer", "part_price", "repair_labor", "repair_quote")
    ]
    missing = [s.title for s in scenarios if s.id not in p["quotes"] and s.id != "charger_accessory"]
    if missing:
        base.notes.append("Insufficient repair price data for: " + ", ".join(missing) + ".")
    return base


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_services(req: ServicesRequest, scenario: str) -> ServicesResult:
    if scenario == "provider_failure":
        raise ProviderError("quota", "Simulated failure: the place search quota was exceeded.")
    services = []
    for name, category, dlat, dlng, relevance in fx.SERVICES:
        if category not in req.needs:
            continue
        distance = None
        if req.latitude is not None and req.longitude is not None:
            distance = round(haversine_km(req.latitude, req.longitude, req.latitude + dlat, req.longitude + dlng), 1)
        services.append(
            LocalService(
                name=name,
                category=category,
                address="Simulated address — not a real business",
                phone=None,
                website=None,
                maps_url=None,
                place_id=None,
                business_status=None,
                distance_km=distance,
                distance_kind="straight_line" if distance is not None else None,
                relevance=relevance,
                simulated=True,
            )
        )
    return ServicesResult(
        source="simulated",
        country=req.country,
        area_label=req.area or ("Current location" if req.latitude is not None else req.country),
        retrieved_at=datetime.now(timezone.utc),
        services=services,
        issues=[],
        attribution="Simulated listings. These businesses do not exist.",
    )
