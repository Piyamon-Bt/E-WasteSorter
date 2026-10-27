"""Repair scenarios, action options and the two rankings.

Transparent rules and arithmetic only. AI output is never used as a numeric
input here; numbers come from price records with provenance.
"""

from ..schemas.common import Money
from ..schemas.market import PriceRecord, RepairScenario
from ..schemas.recommendation import ActionOption, AssessmentSnapshot, Ranking, RecommendationResult
from .functional_checks import resolve_observations, safety_state

# ---- Repair scenarios ----

SCENARIOS = {
    "front_glass_or_screen": ("Front glass / screen replacement", "Replace the cracked front glass or screen assembly."),
    "display_panel": ("Display panel replacement", "Replace the display panel."),
    "display_cable": ("Display cable or connection repair", "Repair the display cable or connector."),
    "hinge": ("Hinge or hinge cover repair", "Repair or replace the hinge or its cover."),
    "back_panel": ("Back panel replacement", "Replace the back panel or back glass."),
    "keyboard": ("Keyboard replacement", "Replace the keyboard."),
    "touchpad": ("Touchpad repair", "Repair or replace the touchpad."),
    "battery": ("Battery replacement", "Replace the battery."),
    "charging_port": ("Charging port repair", "Repair or replace the charging port."),
    "charger_accessory": ("Charger or cable problem", "Try another charger and cable first; this may need no repair."),
    "board_level": ("Internal board repair", "Board-level diagnosis and repair by a technician."),
    "speaker": ("Speaker repair", "Repair or replace the speaker."),
    "camera_or_microphone": ("Camera or microphone repair", "Repair or replace the camera or microphone."),
    "port_repair": ("Port repair", "Repair the affected port."),
    "casing": ("Casing repair", "Repair or replace the damaged casing part."),
}

# Failed check -> (need, alternative scenarios). Alternatives are possibilities, not diagnoses.
CHECK_NEEDS = {
    "power_on": ("Does not power on", ["battery", "charging_port", "board_level"]),
    "charging": ("Not charging", ["charger_accessory", "charging_port", "battery", "board_level"]),
    "display": ("Display fault", ["display_panel", "display_cable"]),
    "touch": ("Touch fault", ["front_glass_or_screen", "board_level"]),
    "keyboard": ("Keyboard fault", ["keyboard"]),
    "touchpad": ("Touchpad fault", ["touchpad"]),
    "sound": ("Sound fault", ["speaker", "board_level"]),
    "microphone_camera": ("Camera or microphone fault", ["camera_or_microphone"]),
    "ports": ("Port fault", ["port_repair"]),
}


def _part_scenario(device_type: str, part: str) -> str:
    p = part.lower()
    if any(w in p for w in ("glass", "screen", "display")):
        return "front_glass_or_screen" if device_type == "mobile" else "display_panel"
    for word, scenario in (("hinge", "hinge"), ("back", "back_panel"), ("keyboard", "keyboard"),
                           ("touchpad", "touchpad"), ("battery", "battery"), ("port", "port_repair")):
        if word in p:
            return scenario
    return "casing"


def derive_repair_scenarios(device_type: str, damaged_parts: list[str], failed_checks: list[str]) -> list[RepairScenario]:
    result: dict[str, RepairScenario] = {}

    def add(need: str, scenario_id: str):
        title, desc = SCENARIOS[scenario_id]
        key = f"{need}:{scenario_id}"
        result.setdefault(key, RepairScenario(id=scenario_id, need=need, title=title, description=desc))

    for part in damaged_parts:
        add(f"Visible damage: {part}", _part_scenario(device_type, part))
    for check in failed_checks:
        if check in CHECK_NEEDS:
            need, alternatives = CHECK_NEEDS[check]
            for s in alternatives:
                add(need, s)
    return list(result.values())


# ---- Money helpers ----


def _span(records: list[PriceRecord], currency: str) -> Money | None:
    if not records:
        return None
    return Money(min=min(r.amount_min for r in records), max=max(r.amount_max for r in records), currency=currency)


def _add(a: Money, b: Money) -> Money:
    return Money(min=a.min + b.min, max=a.max + b.max, currency=a.currency)


def _minus(value: Money, cost: Money) -> Money:
    # Worst case pairs the lowest value with the highest cost.
    return Money(min=value.min - cost.max, max=value.max - cost.min, currency=value.currency)


def _mid(m: Money) -> float:
    return (m.min + m.max) / 2


def _money_text(m: Money | None) -> str:
    return f"{m.currency} {m.min:,.0f}–{m.max:,.0f}" if m else "insufficient data"


def scenario_cost(records: list[PriceRecord], scenario_id: str, currency: str) -> tuple[Money | None, list[str]]:
    """Combined quote if available, else part + labor. Never part + combined quote (no double counting)."""
    rel = [r for r in records if r.scenario_id == scenario_id]
    quotes = [r for r in rel if r.price_type == "repair_quote"]
    notes = []
    if quotes:
        cost = _span(quotes, currency)
    else:
        parts = [r for r in rel if r.price_type == "part_price"]
        labor = [r for r in rel if r.price_type == "repair_labor"]
        if not parts:
            return None, notes
        cost = _span(parts, currency)
        if labor:
            cost = _add(cost, _span(labor, currency))
        else:
            notes.append("labor not included")
    qualities = {r.part_quality for r in rel if r.part_quality in ("genuine", "aftermarket")}
    if len(qualities) > 1:
        notes.append("range spans genuine and aftermarket parts")
    return cost, notes


def repair_cost(
    scenarios: list[RepairScenario], records: list[PriceRecord], currency: str
) -> tuple[Money | None, list[str]]:
    """Sums the cost of each need. Alternatives within one need form a range."""
    needs: dict[str, list[RepairScenario]] = {}
    for s in scenarios:
        needs.setdefault(s.need, []).append(s)
    total: Money | None = Money(min=0, max=0, currency=currency)
    notes: list[str] = []
    for need, alternatives in needs.items():
        known = []
        for s in alternatives:
            if s.id == "charger_accessory":
                continue
            cost, cost_notes = scenario_cost(records, s.id, currency)
            if cost is None:
                notes.append(f"{need}: no price evidence for “{s.title}”.")
            else:
                known.append(cost)
                notes.extend(f"{s.title}: {n}" for n in cost_notes)
        if not known:
            total = None
            notes.append(f"{need}: repair cost unknown.")
            continue
        if total is not None:
            total = _add(total, Money(min=min(k.min for k in known), max=max(k.max for k in known), currency=currency))
        if len(alternatives) > 1:
            notes.append(f"{need}: cost depends on which of {len(alternatives)} possible causes applies.")
    return total, notes


# ---- Recommendation ----

TITLES = {
    "reuse": "Keep using it (reuse)",
    "resell_as_is": "Resell as-is",
    "repair_then_reuse": "Repair, then keep using",
    "repair_then_resell": "Repair, then resell",
    "recycle": "Recycle",
}
RESOURCE_ORDER = ["reuse", "repair_then_reuse", "repair_then_resell", "resell_as_is", "recycle"]
SALE_TYPES = ("completed_sale", "asking_price", "buyback_offer")


def recommend(snap: AssessmentSnapshot) -> RecommendationResult:
    resolved = resolve_observations(snap.physical.observations, snap.reviews)
    safety = safety_state(snap.physical.observations, snap.reviews)
    accepted_damage = [r.observation for r in resolved if r.state in ("accepted", "unreviewed") and r.observation.kind == "physical_damage"]
    disputed_damage = [r.observation for r in resolved if r.state == "disputed" and r.observation.kind == "physical_damage"]
    cosmetic = [r.observation for r in resolved if r.state != "withdrawn" and r.observation.kind == "cosmetic_wear"]

    func = snap.functional
    status = {o.check_id: o.status for o in func.outcomes} if func else {}
    failed = [k for k, v in status.items() if v == "fail"]
    power_failed = status.get("power_on") == "fail"
    func_complete = bool(func and func.complete)
    works = func_complete and not failed

    findings: list[str] = []
    if func is None or not func_complete:
        findings.append("Functional checks are incomplete, so results are conditional on how the device actually works.")
    if cosmetic and not accepted_damage and not disputed_damage and not safety.risks:
        findings.append("Only cosmetic wear was recorded. Cosmetic wear alone does not call for repair.")
    for obs in disputed_damage:
        findings.append(f"Disputed observation: {obs.part}. If confirmed, repair costs and resale value change.")
    if snap.identity.status == "unknown":
        findings.append("Model unknown: model-specific prices were not searched, so the financial ranking is incomplete.")
    elif not snap.identity.evidence_verified:
        findings.append("Prices assume the model you selected. It was not verified from the photos.")

    # Prices
    prices = snap.prices
    records = prices.records if prices else []
    currency = records[0].currency if records else ""
    records = [r for r in records if r.currency == currency]
    scenarios = derive_repair_scenarios(snap.device_type, [o.part for o in accepted_damage], failed)
    cost, cost_notes = repair_cost(scenarios, records, currency) if scenarios and records else (None, [])
    if scenarios and not records:
        cost_notes = ["No repair price evidence available."]

    faulty = bool(accepted_damage or failed)
    state = "damaged_or_faulty" if faulty else ("working" if works else None)
    sale_recs = [r for r in records if r.price_type in SALE_TYPES]
    working_sale = _span([r for r in sale_recs if r.device_state in ("working", "any")], currency)
    as_is_sale = (
        _span([r for r in sale_recs if r.device_state in (state, "any")], currency)
        if state
        else _span(sale_recs, currency)  # unknown function: span damaged to working
    )
    replacement = _span([r for r in records if r.price_type == "asking_price" and r.device_state in ("working", "any")], currency)

    options: list[ActionOption] = []

    def option(action, summary, prereq=(), tradeoffs=(), uncertainty=(), gross=None, rcost=None, net=None, avoided=None, note=""):
        options.append(ActionOption(
            action=action, title=TITLES[action], summary=summary, prerequisites=list(prereq),
            tradeoffs=list(tradeoffs), uncertainty=list(uncertainty), gross_sale=gross,
            repair_cost=rcost, net_proceeds=net, avoided_cost=avoided, financial_note=note,
        ))

    needs_repair = bool(scenarios)
    inspection = "Professional inspection of the suspected safety risk before any power-on or charging."
    unknown_func = [] if func_complete else ["Function not fully checked; outcome depends on actual function."]

    if not safety.blocked and not power_failed:
        cond = [] if works else ["Confirm the device works for your needs."]
        option("reuse", "Keep using the device as it is.", prereq=cond,
               tradeoffs=["No cash income; avoids buying a replacement."] + (["Visible damage stays unrepaired."] if accepted_damage else []),
               uncertainty=unknown_func, avoided=replacement,
               note="Reuse earns no sale proceeds. The value shown is the avoided cost of buying a similar used device (asking prices), not income.")
        option("resell_as_is", "Sell the device in its current condition with an honest description.",
               prereq=["Back up and erase your data; remove accounts and SIM/memory cards."],
               tradeoffs=["Buyer takes on any repair."],
               uncertainty=unknown_func + (["Range spans damaged to working prices because function is unknown."] if state is None else []),
               gross=as_is_sale, net=as_is_sale,
               note="Gross range from local asking prices, buyback offers or evidenced sales; selling fees are not included. Asking prices are not completed sales.")
    elif power_failed and not safety.blocked:
        option("resell_as_is", "Sell as not working / for parts, stating that it does not power on.",
               prereq=["Describe the fault honestly."], tradeoffs=["Lower price than a working device."],
               uncertainty=["Cause of the power failure is unknown."], gross=as_is_sale, net=as_is_sale,
               note="Gross range for damaged or faulty devices; fees not included.")

    if needs_repair:
        prereq = ([inspection] if safety.blocked else []) + ["Get a quote for the specific fault before paying for repair."]
        if power_failed or "charging" in failed:
            prereq.append("Have a technician diagnose the cause; a basic symptom does not identify the failed part.")
        option("repair_then_reuse", "Repair the identified issues, then keep using the device.", prereq=prereq,
               tradeoffs=["Pays repair cost; extends the device's life."], uncertainty=cost_notes + unknown_func,
               rcost=cost, avoided=_minus(replacement, cost) if replacement and cost else None,
               note="No sale proceeds. Value is the avoided replacement cost minus the repair cost.")
        option("repair_then_resell", "Repair the identified issues, then sell the device.", prereq=prereq,
               tradeoffs=["Repair cost is paid before sale; price is not guaranteed."], uncertainty=cost_notes + unknown_func,
               gross=working_sale, rcost=cost, net=_minus(working_sale, cost) if working_sale and cost else None,
               note="Net proceeds = gross sale (working device) minus repair cost. Labor is counted once.")
    elif safety.blocked:
        option("repair_then_reuse", "Have the device inspected and repaired, then keep using it.",
               prereq=[inspection], tradeoffs=["Inspection may find the repair is not worthwhile."],
               uncertainty=["Repair needs and costs are unknown until inspection."], note="Insufficient data for repair costs.")

    option("recycle", "Take the device to an e-waste recycler or collection point.",
           prereq=(["Tell the recycler about the suspected battery issue."] if safety.blocked else [])
           + ["Erase your data first if the device still works.", "Use a recycler that accepts this device type."],
           tradeoffs=["Ends the device's life; materials may be recovered."],
           uncertainty=["Recycler payment, if any, is not quantified."],
           note="Recycling usually returns little or no money. Not quantified.")

    if safety.blocked:
        findings.append("A suspected safety risk limits the options: no reuse or as-is resale before inspection.")

    # Financial ranking: cash outcomes only. Reuse earns no cash, so it is explained, not mixed in.
    cash_actions = ("resell_as_is", "repair_then_resell", "recycle")
    cash = [o for o in options if o.action in cash_actions]
    valued = sorted([o for o in cash if o.net_proceeds], key=lambda o: _mid(o.net_proceeds), reverse=True)
    unranked = [o.action for o in cash if not o.net_proceeds]
    fin_expl = ["Ordered by the midpoint of each net-proceeds range in local currency. Ranges are estimates, not quotes."]
    for a, b in zip(valued, valued[1:]):
        if a.net_proceeds.min <= b.net_proceeds.max:
            fin_expl.append(f"{a.title} and {b.title} have overlapping ranges, so their order depends on actual prices and repair cost.")
    if unranked:
        fin_expl.append("Not ranked (insufficient price data): " + ", ".join(TITLES[a] for a in unranked) + ".")
    for o in options:
        if o.action in ("reuse", "repair_then_reuse"):
            fin_expl.append(
                f"{o.title} is not ranked here because it earns no cash. Its value is the avoided cost of buying a "
                f"similar used device ({_money_text(o.avoided_cost)}), which only applies if you would otherwise buy one."
            )
    financial = Ranking(basis="financial_value", order=[o.action for o in valued], unranked=unranked,
                        explanation=fin_expl, complete=not [a for a in unranked if a != "recycle"] and bool(valued))

    present = {o.action for o in options}
    resource = Ranking(
        basis="resource_use",
        order=[a for a in RESOURCE_ORDER if a in present],
        unranked=[],
        explanation=[
            "Ordered by life extension: keeping a device in use comes before repair, resale and then recycling.",
            "This is a qualitative order. No environmental savings are quantified.",
        ],
        complete=True,
    )
    differ = None
    if financial.order and resource.order and financial.order[0] != resource.order[0]:
        differ = (f"The rankings differ: {TITLES[financial.order[0]]} scores best on available price evidence, "
                  f"while {TITLES[resource.order[0]]} extends the device's life the most. There is no universal "
                  "weighting between money and resource use; choose what matters to you.")

    simulated = any([
        snap.physical.source == "simulated",
        bool(prices and prices.source == "simulated"),
        bool(snap.services and snap.services.source == "simulated"),
    ])
    disclaimers = [
        "Value ranges are estimates from listed evidence, not guaranteed sale prices or repair quotations.",
        "Function results are user-reported, not remotely verified.",
        "Physical findings come from external photos only.",
    ]
    if simulated:
        disclaimers.insert(0, "DEMO MODE: findings, prices and services are simulated and are not real evidence.")
    return RecommendationResult(
        options=options, financial_ranking=financial, resource_ranking=resource,
        safety_constrained=safety.blocked, conditional_findings=findings,
        rankings_differ=differ, disclaimers=disclaimers,
    )
