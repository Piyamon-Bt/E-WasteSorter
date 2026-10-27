"""Markdown report export. Built on request from the browser's snapshot; never stored."""

from datetime import datetime, timezone

from ..schemas.common import Money
from ..schemas.recommendation import AssessmentSnapshot, RecommendationResult
from .functional_checks import resolve_observations, safety_state
from .recommendations import TITLES

KIND_LABELS = {
    "physical_damage": "Physical damage",
    "suspected_safety_risk": "Suspected safety risk",
    "cosmetic_wear": "Cosmetic wear",
    "unassessable": "Not assessable",
}
PRICE_TYPE_LABELS = {
    "asking_price": "Asking price (active listing)",
    "completed_sale": "Completed sale",
    "buyback_offer": "Buyback offer",
    "part_price": "Part price",
    "repair_labor": "Repair labor",
    "repair_quote": "Repair quote (part + labor)",
}


def _money(m: Money | None) -> str:
    if m is None:
        return "Insufficient data"
    return f"{m.currency} {m.min:,.0f} – {m.max:,.0f}"


def _cell(text: str | None) -> str:
    return (text or "").replace("|", "/").replace("\n", " ")


def build_report(snap: AssessmentSnapshot, rec: RecommendationResult | None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    simulated = snap.physical.source == "simulated" or (snap.prices and snap.prices.source == "simulated") or (
        snap.services and snap.services.source == "simulated"
    )
    lines: list[str] = []
    add = lines.append

    add("# E-waste Sorter assessment report")
    add("")
    if simulated:
        add("> **DEMO MODE — SIMULATED RESULTS.** Findings, prices and services in this report are simulated "
            "fixtures. They are not real evidence and must not be used for decisions.")
        add("")
    add(f"- Generated: {now}")
    add(f"- Device type: {snap.device_type}")
    add(f"- Physical assessment source: {snap.physical.source} ({snap.physical.model or 'n/a'})")
    add("- Photo views: checked for slot assignment only; camera angles were not verified.")
    add("")

    # Physical findings first
    add("## 1. Physical findings (external photos)")
    add("")
    add(snap.physical.summary)
    add("")
    for item in resolve_observations(snap.physical.observations, snap.reviews):
        o = item.observation
        review = item.review
        add(f"### {KIND_LABELS[o.kind]}: {o.part}")
        add(f"- Observation: {o.description}")
        add(f"- Evidence: {o.visible_evidence} (photos: {', '.join(o.views) or 'none'})")
        add(f"- Uncertainty: {o.uncertainty} — {o.uncertainty_reason}")
        add(f"- Your review: {review.response if review and review.response else 'not reviewed'}"
            + (f" — “{_cell(review.note)}”" if review and review.note else ""))
        for n, f in enumerate(review.follow_ups if review else [], start=1):
            revised = f" → revised to {KIND_LABELS[f.revised_observation.kind]}: {f.revised_observation.part}" if f.revised_observation else ""
            add(f"- Follow-up {n} ({f.extra_images} extra photo(s), {f.source}): {f.outcome}{revised} — {f.explanation}")
        add(f"- Status used in recommendations: {item.state}")
        add("")
    if snap.physical.unassessable_areas:
        add("**Not assessable from photos:** " + "; ".join(snap.physical.unassessable_areas))
        add("")

    safety = safety_state(snap.physical.observations, snap.reviews)
    if safety.risks:
        add("### Safety")
        for r in safety.risks:
            add(f"- {r.part}: {r.status.replace('_', ' ')} — {r.explanation}")
        for g in safety.guidance:
            add(f"- {g}")
        add("")

    # Functional results
    add("## 2. Functional checks (user-reported)")
    add("")
    if snap.functional:
        add("| Check | Result | Note |")
        add("|---|---|---|")
        for o in snap.functional.outcomes:
            add(f"| {o.label} | {o.status.replace('_', ' ')} | {_cell(o.note)} |")
        add("")
        for c in snap.functional.conditional_findings + snap.functional.clarifications:
            add(f"- {c}")
        add(f"- {snap.functional.disclaimer}")
    else:
        add("Not completed. Function is unknown, which is not the same as working.")
    add("")

    # Identity
    ident = snap.identity
    add("## 3. Device identity")
    add("")
    add(f"- User-confirmed identity: {ident.label()} ({ident.status.replace('_', ' ')})")
    add(f"- Verified from photo evidence: {'yes' if ident.evidence_verified else 'no'}")
    add(f"- Photo evidence strength: {snap.physical.identity.evidence_strength}")
    add("")

    # Location
    if snap.location:
        add("## 4. Market")
        add("")
        add(f"- Country: {snap.location.country}; area: {snap.location.area or 'not specified'}"
            + ("; device location used for distance" if snap.location.used_device_location else ""))
        add("")

    # Prices
    add("## 5. Price evidence")
    add("")
    p = snap.prices
    if p is None:
        add("Not searched.")
    else:
        add(f"- Status: {p.status.replace('_', ' ')}; source: {p.source}; retrieved: {p.retrieved_at:%Y-%m-%d %H:%M UTC}")
        for issue in p.issues:
            add(f"- Problem ({issue.code}): {issue.message}")
        for n in p.notes:
            add(f"- {n}")
        if p.records:
            add("")
            add("| Type | Item | Price | State / part | Match | Source | Retrieved | Limitations |")
            add("|---|---|---|---|---|---|---|---|")
            for r in p.records:
                tag = " (SIMULATED)" if r.simulated else ""
                add(
                    f"| {PRICE_TYPE_LABELS[r.price_type]} | {_cell(r.item)} | {r.currency} {r.amount_min:,.0f}–{r.amount_max:,.0f} "
                    f"({r.market}) | {r.device_state} / {r.part_quality} | {r.match_level}: {_cell(r.matching_conditions)} "
                    f"| [{_cell(r.source_title) or 'source'}{tag}]({r.source_url}) | {r.retrieved_at:%Y-%m-%d} | {_cell(r.limitations)} |"
                )
        insufficient = [PRICE_TYPE_LABELS[c.price_type] for c in p.channels if c.status == "insufficient_data"]
        if insufficient:
            add("")
            add("Insufficient data: " + ", ".join(insufficient) + ".")
        if p.repair_scenarios:
            add("")
            add("Possible repair scenarios (not diagnoses):")
            for s in p.repair_scenarios:
                add(f"- {s.title} — may address: {'; '.join(s.needs)}")
    add("")

    # Services
    add("## 6. Local services")
    add("")
    s = snap.services
    if s is None:
        add("Not searched.")
    else:
        for issue in s.issues:
            add(f"- Problem ({issue.code}): {issue.message}")
        for svc in s.services:
            dist = f"{svc.distance_km} km straight-line" if svc.distance_km is not None else "distance not available"
            link = f" — [map]({svc.maps_url})" if svc.maps_url else ""
            add(f"- **{svc.name}** ({svc.category}{', SIMULATED' if svc.simulated else ''}): {svc.address or 'no address'}; "
                f"{svc.phone or 'no phone'}; {dist}{link}. {svc.relevance}")
        for n in s.notes:
            add(f"- {n}")
        if s.attribution:
            add(f"- {s.attribution}")
        add(f"- Retrieved: {s.retrieved_at:%Y-%m-%d %H:%M UTC}. The app did not contact any business.")
    add("")

    # Recommendations
    add("## 7. Options and rankings")
    add("")
    if rec is None:
        add("Not generated.")
    else:
        for d in rec.disclaimers:
            add(f"- {d}")
        for c in rec.conditional_findings:
            add(f"- {c}")
        add("")
        for o in rec.options:
            add(f"### {o.title}")
            add(o.summary)
            add(f"- Financial status: {o.financial_status}"
                + (f"; comparison basis: {PRICE_TYPE_LABELS[o.sale_basis]}" if o.sale_basis else ""))
            for c in o.sale_channels:
                add(f"- Sale channel — {PRICE_TYPE_LABELS[c.price_type]} ({c.device_state.replace('_', ' ')}, "
                    f"{c.records} record(s)): {_money(c.range)}{' — used for calculation' if c.used_for_calculation else ''}")
            add(f"- Gross sale: {_money(o.gross_sale)}; repair cost: {_money(o.repair_cost)}"
                f"{'' if o.repair_cost_complete else ' (incomplete)'}; "
                f"net proceeds: {_money(o.net_proceeds)}; avoided cost: {_money(o.avoided_cost)}")
            add(f"- {o.financial_note}")
            for x in o.prerequisites:
                add(f"- Prerequisite: {x}")
            for x in o.tradeoffs:
                add(f"- Tradeoff: {x}")
            for x in o.uncertainty:
                add(f"- Uncertainty: {x}")
            add("")
        for ranking, title in ((rec.financial_ranking, "Financial value"), (rec.resource_ranking, "Resource use / life extension")):
            add(f"**{title} ranking:** " + (" > ".join(TITLES[a] for a in ranking.order) or "none")
                + ("" if ranking.complete else " (incomplete)"))
            if ranking.conditional:
                add("- Conditional order (incomplete evidence): " + " > ".join(TITLES[a] for a in ranking.conditional))
            for e in ranking.explanation:
                add(f"- {e}")
            add("")
        if rec.rankings_differ:
            add(rec.rankings_differ)
            add("")
        if rec.disposal_guidance:
            add("**General disposal guidance (not a recommendation):**")
            for g in rec.disposal_guidance:
                add(f"- {g}")
            add("")
    add("---")
    add("This report is not a repair quotation, sale offer or safety certification. The assessment was not stored by the app.")
    return "\n".join(lines) + "\n"
