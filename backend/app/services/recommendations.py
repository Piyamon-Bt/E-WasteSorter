"""Repair scenarios, action options and the two rankings.

Transparent rules and arithmetic only. AI output is never used as a numeric
input here; numbers come from price records with provenance.

Financial rules (see docs/ARCHITECTURE.md):
- One repair intervention that may address several findings is priced once.
- Repair cost is "complete" only when every plausible combination of causes is
  priced with a combined quote or part + labor. Otherwise it is conditional.
- Sale channels (completed sales, buyback offers, asking prices) are never pooled.
  Sale options are compared on one common channel, chosen in that order.
  Asking prices are not proceeds, so an asking-price basis is conditional.
- An option is "complete" only when the evidence behind it is sufficient: functional checks
  complete without contradictions, no disputed damage, and (for repairs) confirmed causes.
  Otherwise it stays conditional and its assumptions are listed.
- A replacement charger/cable is priced only from accessory evidence, never assumed free.
- Recycle is not offered as a ranked option: this MVP cannot establish end-of-life evidence.
  "Repair may not be worthwhile" is reported as an economic finding; disposal guidance is separate.
"""

import itertools
from dataclasses import dataclass, field

from ..schemas.common import Money
from ..schemas.market import PriceRecord, RepairScenario
from ..schemas.recommendation import (
    ActionOption,
    AssessmentSnapshot,
    Ranking,
    RecommendationResult,
    SaleChannelEstimate,
)
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
    "charger_accessory": ("Replacement charger or cable", "Buy a replacement charger or cable if the original accessory is the cause."),
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


def derive_repair_scenarios(
    device_type: str, damaged_parts: list[str], failed_checks: list[str], accessory_ruled_out: bool = False
) -> list[RepairScenario]:
    """One scenario per intervention; `needs` lists every finding it might address.

    `accessory_ruled_out`: charging failed with a charger the user knows works, so a replacement
    charger or cable is not a plausible cause.
    """
    result: dict[str, RepairScenario] = {}

    def add(need: str, scenario_id: str):
        title, desc = SCENARIOS[scenario_id]
        scenario = result.setdefault(scenario_id, RepairScenario(id=scenario_id, needs=[], title=title, description=desc))
        if need not in scenario.needs:
            scenario.needs.append(need)

    for part in damaged_parts:
        add(f"Visible damage: {part}", _part_scenario(device_type, part))
    for check in failed_checks:
        if check in CHECK_NEEDS:
            need, alternatives = CHECK_NEEDS[check]
            for s in alternatives:
                if s == ACCESSORY and accessory_ruled_out:
                    continue
                add(need, s)
    return list(result.values())


# ---- Money helpers ----

# Only records that match the device closely enough are used in calculations.
CALC_MATCH = ("exact", "close")
ACCESSORY = "charger_accessory"  # an accessory purchase: its price is the full cost, no labor needed


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


# ---- Repair cost ----


def scenario_cost(records: list[PriceRecord], scenario_id: str, currency: str) -> tuple[Money | None, bool, list[str]]:
    """Cost of one intervention: (range, partial, notes).

    Per part quality: a combined repair quote if available, else part price + labor.
    Part and combined quote are never added together. Different part qualities are
    alternatives and are named in the notes. A part price without labor is partial.
    """
    rel = [r for r in records if r.scenario_id == scenario_id and r.match_level in CALC_MATCH]
    labor = _span([r for r in rel if r.price_type == "repair_labor"], currency)
    qualities = sorted({r.part_quality for r in rel if r.price_type in ("repair_quote", "part_price")})
    costs: list[tuple[str, Money, str]] = []
    partial = False
    for q in qualities:
        quotes = [r for r in rel if r.price_type == "repair_quote" and r.part_quality == q]
        parts = [r for r in rel if r.price_type == "part_price" and r.part_quality == q]
        if quotes:
            costs.append((q, _span(quotes, currency), "repair quote"))
        elif parts and scenario_id == ACCESSORY:
            costs.append((q, _span(parts, currency), "accessory purchase"))
        elif parts and labor:
            costs.append((q, _add(_span(parts, currency), labor), "part + labor"))
        elif parts:
            partial = True
            costs.append((q, _span(parts, currency), "part only, labor not included"))
    if not costs:
        return None, False, []
    cost = Money(min=min(c.min for _, c, _ in costs), max=max(c.max for _, c, _ in costs), currency=currency)
    notes = []
    if len(costs) > 1:
        notes.append("alternatives by part quality: " + "; ".join(f"{q} ({how}) {_money_text(c)}" for q, c, how in costs))
    elif costs[0][2] not in ("repair quote", "accessory purchase"):
        notes.append(costs[0][2])
    return cost, partial, notes


@dataclass
class RepairCostEstimate:
    cost: Money | None  # range across the fully priced combinations of causes
    complete: bool  # every combination priced with full (non-partial) costs
    notes: list[str] = field(default_factory=list)


def repair_cost(scenarios: list[RepairScenario], records: list[PriceRecord], currency: str) -> RepairCostEstimate:
    """Range over every combination of one cause per need, counting a shared intervention once."""
    if not scenarios:
        return RepairCostEstimate(None, True)
    needs: dict[str, list[str]] = {}
    for s in scenarios:
        for need in s.needs:
            needs.setdefault(need, []).append(s.id)
    # No scenario is assumed free: an unpriced accessory stays unknown.
    priced = {s.id: scenario_cost(records, s.id, currency) for s in scenarios}

    lows, highs = [], []
    unpriced = partial = False
    for combo in itertools.product(*needs.values()):
        chosen = set(combo)  # a shared intervention is paid once
        if any(priced[s][0] is None for s in chosen):
            unpriced = True
            continue
        lows.append(sum(priced[s][0].min for s in chosen))
        highs.append(sum(priced[s][0].max for s in chosen))
        partial = partial or any(priced[s][1] for s in chosen)
    cost = Money(min=min(lows), max=max(highs), currency=currency) if lows else None

    notes: list[str] = []
    for s in scenarios:
        money, is_partial, s_notes = priced[s.id]
        if money is None:
            notes.append(f"No price evidence for “{s.title}” (possible cause of: {', '.join(s.needs)}).")
        elif is_partial:
            notes.append(f"{s.title}: part price only, labor not included — partial cost.")
        notes.extend(f"{s.title}: {n}" for n in s_notes if not (is_partial and n.startswith("part only")))
        if len(s.needs) > 1:
            notes.append(
                f"{s.title} may address {' and '.join(s.needs)}; it is counted once. "
                "It may not fix every finding if the causes differ."
            )
    for need, ids in needs.items():
        if len(ids) > 1:
            notes.append(f"{need}: cost depends on which of {len(ids)} possible causes applies.")
    if cost is None:
        notes.append("Repair cost unknown: no fully priced combination of repairs.")
    elif unpriced:
        notes.append("Range covers only the priced combinations of causes; the real cost could be higher.")
    if partial:
        notes.append("Some costs are partial (labor missing), so the repair cost is incomplete.")
    return RepairCostEstimate(cost, cost is not None and not unpriced and not partial, notes)


def unconfirmed_causes(scenarios: list[RepairScenario]) -> list[str]:
    """Needs with more than one possible cause: the actual fault is not confirmed."""
    counts: dict[str, int] = {}
    for s in scenarios:
        for need in s.needs:
            counts[need] = counts.get(need, 0) + 1
    return [need for need, n in counts.items() if n > 1]


# ---- Sale channels ----

# Comparison basis, most reliable first: evidenced sales, then published offers, then asking prices.
CHANNEL_PRIORITY = ("completed_sale", "buyback_offer", "asking_price")
CHANNEL_LABELS = {"completed_sale": "completed sales", "buyback_offer": "buyback offers", "asking_price": "asking prices"}


def channel_estimates(records: list[PriceRecord], state: str, currency: str) -> list[SaleChannelEstimate]:
    """One range per channel for exactly this device condition. Channels are never merged."""
    out = []
    for t in CHANNEL_PRIORITY:
        recs = [r for r in records if r.price_type == t and r.device_state == state and r.match_level in CALC_MATCH]
        if recs:
            out.append(SaleChannelEstimate(price_type=t, device_state=state, range=_span(recs, currency),
                                           records=len(recs), used_for_calculation=False))
    return out


def common_basis(channel_sets: list[list[SaleChannelEstimate]]) -> str | None:
    """The most reliable channel available for every sale option being compared."""
    for t in CHANNEL_PRIORITY:
        if channel_sets and all(any(c.price_type == t for c in cs) for cs in channel_sets):
            return t
    return None


def pick(channels: list[SaleChannelEstimate], basis: str | None) -> SaleChannelEstimate | None:
    """Marks and returns the channel used: the common basis, or this option's own best channel."""
    chosen = next((c for c in channels if c.price_type == basis), None) if basis else (channels[0] if channels else None)
    if chosen:
        chosen.used_for_calculation = True
    return chosen


# ---- Recommendation ----

TITLES = {
    "reuse": "Keep using it (reuse)",
    "resell_as_is": "Resell as-is",
    "repair_then_reuse": "Repair, then keep using",
    "repair_then_resell": "Repair, then resell",
    "recycle": "Recycle",
}
RESOURCE_ORDER = ["reuse", "repair_then_reuse", "repair_then_resell", "resell_as_is", "recycle"]
DISPOSAL_GUIDANCE = [
    "If you later decide the device has reached end of life, use a certified e-waste collection point or a "
    "manufacturer or retailer take-back programme. Do not put it in household waste.",
    "Back up and erase your data, sign out of accounts and remove SIM or memory cards first where possible.",
]
BATTERY_GUIDANCE = (
    "With a suspected battery issue: do not charge it, keep it away from heat, and tell the collection point or "
    "repairer about the battery before handing it over."
)


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

    # Prices (one currency only)
    prices = snap.prices
    records = prices.records if prices else []
    currency = records[0].currency if records else ""
    records = [r for r in records if r.currency == currency]
    if any(r.match_level == "indicative" for r in records):
        findings.append("Indicative prices for nearby models are listed as evidence but not used in calculations.")
    charging = next((o for o in func.outcomes if o.check_id == "charging"), None) if func else None
    accessory_ruled_out = bool(charging and charging.accessory_check == "known_working")
    scenarios = derive_repair_scenarios(snap.device_type, [o.part for o in accepted_damage], failed, accessory_ruled_out)

    # Evidence gaps that keep financial estimates conditional (never only a disclaimer).
    condition_gaps: list[str] = []
    if func is None:
        condition_gaps.append("no functional checks were recorded")
    elif func.clarifications:
        condition_gaps.append("functional answers contradict each other")
    elif not func.complete:
        condition_gaps.append("some functional checks are unknown or unanswered")
    if disputed_damage:
        condition_gaps.append("disputed damage (" + ", ".join(o.part for o in disputed_damage) + ") could change costs and value")
    repair_gaps = condition_gaps + [f"the cause of “{n}” is not confirmed" for n in unconfirmed_causes(scenarios)]
    estimate = repair_cost(scenarios, records, currency) if records else RepairCostEstimate(None, not scenarios)
    cost_notes = estimate.notes if records else (["No repair price evidence available."] if scenarios else [])
    cost = estimate.cost

    faulty = bool(accepted_damage or failed)
    as_is_state = "damaged_or_faulty" if faulty else ("working" if works else None)
    working_channels = channel_estimates(records, "working", currency)
    as_is_channels = channel_estimates(records, as_is_state, currency) if as_is_state else []
    replacement_recs = [r for r in records if r.price_type == "asking_price" and r.device_state == "working" and r.match_level in CALC_MATCH]
    replacement = _span(replacement_recs, currency)

    needs_repair = bool(scenarios)
    offer_as_is = not safety.blocked
    offer_repair_resell = needs_repair
    sale_sets = ([as_is_channels] if offer_as_is and as_is_state else []) + ([working_channels] if offer_repair_resell else [])
    basis = common_basis(sale_sets)

    options: list[ActionOption] = []

    def option(action, summary, prereq=(), tradeoffs=(), uncertainty=(), **money):
        options.append(ActionOption(
            action=action, title=TITLES[action], summary=summary, prerequisites=list(prereq),
            tradeoffs=list(tradeoffs), uncertainty=list(uncertainty), **money,
        ))

    def sale_status(chosen: SaleChannelEstimate | None, extra_conditional: bool) -> str:
        if chosen is None:
            return "insufficient"
        if chosen.price_type == "asking_price" or basis is None or extra_conditional:
            return "conditional"
        return "complete"

    def gaps_note(gaps: list[str]) -> str:
        return (" Conditional because " + "; ".join(gaps) + ". The estimate assumes the device's condition is as recorded.") if gaps else ""

    def basis_note(chosen: SaleChannelEstimate | None) -> str:
        if chosen is None:
            return "No local sale evidence for this condition."
        text = f"Gross sale uses {CHANNEL_LABELS[chosen.price_type]} ({chosen.records} record(s)); other channels are shown separately, not averaged."
        if chosen.price_type == "asking_price":
            text += " Asking prices are listing prices, not verified sale proceeds."
        if basis is None:
            text += " The options could not be compared on one common channel, so the comparison is conditional."
        return text + " Selling fees are not included."

    inspection = "Professional inspection of the suspected safety risk before any power-on or charging."
    unknown_func = [] if func_complete else ["Function not fully checked; outcome depends on actual function."]
    reuse_note = ("Reuse earns no sale proceeds. The value shown is the avoided cost of buying a similar used device, "
                  "based on asking prices, not income.")

    if not safety.blocked and not power_failed:
        cond = [] if works else ["Confirm the device works for your needs."]
        option("reuse", "Keep using the device as it is.", prereq=cond,
               tradeoffs=["No cash income; avoids buying a replacement."] + (["Visible damage stays unrepaired."] if accepted_damage else []),
               uncertainty=unknown_func, gross_sale=None, repair_cost=None, net_proceeds=None, avoided_cost=replacement,
               financial_status="conditional" if replacement else "insufficient", financial_note=reuse_note)

    if offer_as_is:
        if as_is_state is None:
            # Unknown function: show both condition scenarios instead of one merged value.
            scenarios_by_state = channel_estimates(records, "working", currency) + channel_estimates(records, "damaged_or_faulty", currency)
            option("resell_as_is", "Sell the device in its current condition with an honest description.",
                   prereq=["Back up and erase your data; remove accounts and SIM/memory cards.", "Check how it works so it can be described honestly."],
                   tradeoffs=["Buyer takes on any repair."],
                   uncertainty=unknown_func + ["The sale value depends on whether it works; both condition scenarios are shown."],
                   sale_channels=scenarios_by_state, gross_sale=None, repair_cost=None, net_proceeds=None, avoided_cost=None,
                   financial_status="conditional" if scenarios_by_state else "insufficient",
                   financial_note="Not ranked: without complete functional checks the device condition, and so its price, is unknown.")
        else:
            chosen = pick(as_is_channels, basis)
            summary = ("Sell as not working / for parts, stating that it does not power on." if power_failed
                       else "Sell the device in its current condition with an honest description.")
            option("resell_as_is", summary,
                   prereq=["Back up and erase your data; remove accounts and SIM/memory cards."] if not power_failed else ["Describe the fault honestly."],
                   tradeoffs=["Buyer takes on any repair."] if not power_failed else ["Lower price than a working device."],
                   uncertainty=unknown_func + (["Cause of the power failure is unknown."] if power_failed else []),
                   sale_channels=as_is_channels, sale_basis=chosen.price_type if chosen else None,
                   gross_sale=chosen.range if chosen else None, repair_cost=None,
                   net_proceeds=chosen.range if chosen else None, avoided_cost=None,
                   financial_status=sale_status(chosen, bool(condition_gaps)),
                   financial_note=basis_note(chosen) + gaps_note(condition_gaps))

    if needs_repair:
        prereq = ([inspection] if safety.blocked else []) + ["Get a quote for the specific fault before paying for repair."]
        if power_failed or "charging" in failed:
            prereq.append("Have a technician diagnose the cause; a basic symptom does not identify the failed part.")
        if "charging" in failed and not accessory_ruled_out:
            prereq.append("Before buying anything, test with a charger and cable you know work. This check costs nothing "
                          "if you can borrow one; if charging then works, only the accessory needs replacing.")
        cost_flag = "" if estimate.complete else " The repair cost is incomplete, so this comparison is conditional."
        if repair_gaps:
            cost_flag += " A priced repair does not prove the device will work afterwards." + gaps_note(repair_gaps)
        avoided = _minus(replacement, cost) if replacement and cost else None
        option("repair_then_reuse", "Repair the identified issues, then keep using the device.", prereq=prereq,
               tradeoffs=["Pays repair cost; extends the device's life."], uncertainty=cost_notes + unknown_func,
               gross_sale=None, repair_cost=cost, repair_cost_complete=estimate.complete, net_proceeds=None, avoided_cost=avoided,
               financial_status="conditional" if avoided else "insufficient",
               financial_note="No sale proceeds. Value is the avoided replacement cost (asking prices) minus the repair cost." + cost_flag)
        chosen = pick(working_channels, basis)
        net = _minus(chosen.range, cost) if chosen and cost else None
        option("repair_then_resell", "Repair the identified issues, then sell the device.", prereq=prereq,
               tradeoffs=["Repair cost is paid before sale; price is not guaranteed."], uncertainty=cost_notes + unknown_func,
               sale_channels=working_channels, sale_basis=chosen.price_type if chosen else None,
               gross_sale=chosen.range if chosen else None, repair_cost=cost, repair_cost_complete=estimate.complete,
               net_proceeds=net, avoided_cost=None,
               financial_status=sale_status(chosen, not estimate.complete or bool(repair_gaps)) if net else "insufficient",
               financial_note="Net proceeds = gross sale of a working device minus repair cost. " + basis_note(chosen) + cost_flag)
    elif safety.blocked:
        option("repair_then_reuse", "Have the device inspected and repaired, then keep using it.",
               prereq=[inspection], tradeoffs=["Inspection may find the repair is not worthwhile."],
               uncertainty=["Repair needs and costs are unknown until inspection."],
               gross_sale=None, repair_cost=None, net_proceeds=None, avoided_cost=None,
               financial_status="insufficient", financial_note="Insufficient data for repair costs.")

    # Repair economics are an economic finding only. Price evidence alone cannot show that a device
    # has reached end of life, so Recycle is not offered; general disposal guidance stays separate.
    working_value = pick(working_channels, basis) if needs_repair else None
    if needs_repair and cost and working_value and cost.min >= working_value.range.max:
        findings.append(
            f"Repair may not be financially worthwhile: the lowest repair cost ({_money_text(cost)}) is at least the "
            f"highest value of a working device ({_money_text(working_value.range)}). Reuse, as-is resale or passing "
            "the device on may still make sense; this alone does not mean the device has reached end of life."
        )

    if safety.blocked:
        findings.append("A suspected safety risk limits the options: no reuse or as-is resale before inspection.")

    # Financial ranking: cash outcomes only, definitive only with complete evidence.
    cash = [o for o in options if o.action in ("resell_as_is", "repair_then_resell", "recycle")]
    definitive = sorted([o for o in cash if o.financial_status == "complete" and o.net_proceeds], key=lambda o: _mid(o.net_proceeds), reverse=True)
    conditional = sorted([o for o in cash if o.financial_status == "conditional" and o.net_proceeds], key=lambda o: _mid(o.net_proceeds), reverse=True)
    unranked = [o.action for o in cash if o not in definitive and o not in conditional]
    basis_text = (f"Sale options are compared on {CHANNEL_LABELS[basis]}, the most reliable channel available for all of them."
                  if basis else "No single sale channel covers all sale options, so they could not be compared on one basis.")
    fin_expl = ["Ordered by the midpoint of each net-proceeds range in local currency. Ranges are estimates, not quotes.", basis_text]
    for group in (definitive, conditional):
        for a, b in zip(group, group[1:]):
            if a.net_proceeds.min <= b.net_proceeds.max:
                fin_expl.append(f"{a.title} and {b.title} have overlapping ranges, so their order depends on actual prices and repair cost.")
    if conditional:
        fin_expl.append("Conditional (asking prices, partial or incomplete repair costs, or no common channel): "
                        + ", ".join(o.title for o in conditional) + ".")
    if unranked:
        fin_expl.append("Not ranked (insufficient price data): " + ", ".join(TITLES[a] for a in unranked) + ".")
    for o in options:
        if o.action in ("reuse", "repair_then_reuse"):
            fin_expl.append(
                f"{o.title} is not ranked here because it earns no cash. Its value is the avoided cost of buying a "
                f"similar used device ({_money_text(o.avoided_cost)}), which only applies if you would otherwise buy one."
            )
    financial = Ranking(
        basis="financial_value", order=[o.action for o in definitive], conditional=[o.action for o in conditional],
        unranked=unranked, explanation=fin_expl,
        complete=bool(definitive) and not conditional and not [a for a in unranked if a != "recycle"],
    )

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
    fin_top = (financial.order or financial.conditional or [None])[0]
    if fin_top and resource.order and fin_top != resource.order[0]:
        differ = (f"The rankings differ: {TITLES[fin_top]} scores best on available price evidence"
                  f"{'' if financial.order else ' (conditional)'}, while {TITLES[resource.order[0]]} extends the "
                  "device's life the most. There is no universal weighting between money and resource use; choose what matters to you.")

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
        disposal_guidance=DISPOSAL_GUIDANCE + ([BATTERY_GUIDANCE] if safety.blocked else []),
    )
