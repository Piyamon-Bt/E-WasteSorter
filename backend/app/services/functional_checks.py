"""Safety gating and basic, non-invasive functional checks.

Everything here is plain rules. Function results are user-reported.
"""

from dataclasses import dataclass

from ..schemas.functional import (
    CheckDefinition,
    CheckOutcome,
    CheckResponse,
    FunctionalEvaluation,
    FunctionalPlan,
    RiskStatus,
    SafetyState,
)
from ..schemas.physical import Observation, ObservationReview

POWER_CHECK = "power_on"

CHECKS: dict[str, list[CheckDefinition]] = {
    "mobile": [
        CheckDefinition(id="power_on", label="Power on", depends_on_power=False,
                        instructions="Press and hold the power button for up to 10 seconds. Does the phone start (logo or screen lights up)?"),
        CheckDefinition(id="charging", label="Charging", depends_on_power=False,
                        instructions="Connect a charger and cable you know work for 10 minutes. Does a charging indicator appear? Choose Unable to test if you have no charger."),
        CheckDefinition(id="display", label="Display", depends_on_power=True,
                        instructions="Is the whole screen visible, without dead areas, lines or flicker?"),
        CheckDefinition(id="touch", label="Touch", depends_on_power=True,
                        instructions="Swipe and tap across the whole screen, including the edges. Does it respond everywhere?"),
        CheckDefinition(id="sound", label="Sound", depends_on_power=True,
                        instructions="Play a sound or video. Is sound clear from the speaker?"),
        CheckDefinition(id="microphone_camera", label="Microphone and cameras", depends_on_power=True,
                        instructions="Record a short video with the front and back cameras. Are picture and sound recorded?"),
        CheckDefinition(id="ports", label="Ports and connections", depends_on_power=True,
                        instructions="Use the ports you can reach (cable, headphone jack if present). Are connections detected?"),
    ],
    "laptop": [
        CheckDefinition(id="power_on", label="Power on", depends_on_power=False,
                        instructions="Press the power button. Does the laptop start (lights, fan, logo)? Try with the charger connected if the battery may be empty."),
        CheckDefinition(id="charging", label="Charging", depends_on_power=False,
                        instructions="Connect a charger you know works. Does a charging light or battery indicator show charging? Choose Unable to test if you have no charger."),
        CheckDefinition(id="display", label="Display", depends_on_power=True,
                        instructions="Is the whole screen visible, without dead areas, lines or flicker?"),
        CheckDefinition(id="keyboard", label="Keyboard", depends_on_power=True,
                        instructions="Type in a text editor. Do all keys register?"),
        CheckDefinition(id="touchpad", label="Touchpad", depends_on_power=True,
                        instructions="Move the pointer and click. Does the touchpad respond?"),
        CheckDefinition(id="sound", label="Sound", depends_on_power=True,
                        instructions="Play a sound or video. Is sound clear from the speakers?"),
        CheckDefinition(id="microphone_camera", label="Microphone and webcam", depends_on_power=True,
                        instructions="Open the camera app and record a short clip. Are picture and sound recorded?"),
        CheckDefinition(id="ports", label="Ports and connections", depends_on_power=True,
                        instructions="Plug a USB device or cable into the ports you can reach. Is it detected?"),
    ],
}

RISK_GUIDANCE = [
    "Do not power on or charge the device until a professional has inspected it.",
    "Do not press, puncture, bend or open the device. Keep it away from heat and flammable materials.",
    "Take it to a repair professional or an e-waste collection point that accepts damaged batteries.",
    "If you think the risk is wrong, add close-up photos of the area (including edge-on views) on the Review step.",
]
CHECK_GUIDANCE = [
    "Only do the checks you can do safely and without opening the device.",
    "Choose Unable to test if you lack an accessory or the device does not have the feature.",
    "Stop if the device gets hot, smells of burning, swells or makes unusual noises.",
]


RISK = "suspected_safety_risk"


@dataclass
class ResolvedObservation:
    observation: Observation  # effective observation after follow-up revisions (original id kept)
    original: Observation
    review: ObservationReview | None
    state: str  # "accepted" | "disputed" | "withdrawn" | "unreviewed"
    # Index in the follow-up history of the latest event that asserted a safety risk:
    # -1 = the original observation, None = never a risk.
    last_risk_event: int | None = None


def resolve_observations(observations: list[Observation], reviews: list[ObservationReview]) -> list[ResolvedObservation]:
    """Applies user reviews and the whole follow-up history without assuming either side is always right.

    Revisions apply in order, so the effective observation is the latest revision. A later
    follow-up that is not a revision (upheld, unresolved) keeps the previous effective observation.
    """
    by_id = {r.observation_id: r for r in reviews}
    resolved = []
    for obs in observations:
        review = by_id.get(obs.id)
        history = review.follow_ups if review else []
        current = obs
        last_risk = -1 if obs.kind == RISK else None
        for i, f in enumerate(history):
            if f.outcome == "revised" and f.revised_observation:
                # Keep the original id so reviews, photos and reports stay linked.
                current = f.revised_observation.model_copy(update={"id": obs.id})
                if current.kind == RISK:
                    last_risk = i
        latest = history[-1] if history else None
        if latest and latest.outcome == "not_supported" and latest.extra_images > 0:
            state = "withdrawn"
        elif review is None or review.response is None:
            state = "unreviewed"
        elif review.response == "agree" or (latest and latest.outcome in ("upheld", "revised")):
            state = "accepted"
        else:
            state = "disputed"
        resolved.append(ResolvedObservation(current, obs, review, state, last_risk))
    return resolved


def safety_state(observations: list[Observation], reviews: list[ObservationReview]) -> SafetyState:
    """Blocks power-on and charging while any original or follow-up-identified risk is not cleared.

    Rules:
    - Once a risk is asserted (originally or by any follow-up revision), it stays in the history.
      Later results never erase it.
    - It is cleared only when the most recent follow-up comes after the latest risk assertion and
      is an explicit "not_supported" outcome based on at least one usable new photo.
    - Disagreement, "unresolved", "upheld" or a revision away from the risk kind do not clear it.
    """
    risks = []
    for item in resolve_observations(observations, reviews):
        if item.last_risk_event is None:
            continue
        history = item.review.follow_ups if item.review else []
        latest_index = len(history) - 1
        latest = history[-1] if history else None
        cleared = (
            latest is not None
            and latest_index > item.last_risk_event
            and latest.outcome == "not_supported"
            and latest.extra_images > 0
        )
        found_in_follow_up = item.last_risk_event >= 0
        if cleared:
            status, why = "cleared_after_follow_up", "The latest follow-up photos did not show the suspected risk. Stay cautious."
        elif found_in_follow_up and item.original.kind != RISK and item.observation.kind == RISK:
            status, why = "identified_in_follow_up", "A follow-up re-check identified a suspected safety risk."
        elif item.review and item.review.response == "agree":
            status, why = "confirmed_by_user", "You agreed with the suspected risk."
        else:
            status = "unresolved"
            why = "Not resolved. Disagreement or uncertainty alone does not clear a safety risk."
            if item.observation.kind != RISK:
                why = ("An earlier re-check identified a suspected safety risk. A later result did not explicitly "
                       "rule it out with new photos, so it stays unresolved.")
        part = item.observation.part if item.observation.kind == RISK else item.original.part
        if found_in_follow_up and item.observation.kind != RISK:
            risk_obs = history[item.last_risk_event].revised_observation
            part = risk_obs.part if risk_obs else part
        risks.append(RiskStatus(observation_id=item.original.id, part=part, status=status, explanation=why))
    blocked = any(r.status != "cleared_after_follow_up" for r in risks)
    return SafetyState(blocked=blocked, risks=risks, guidance=RISK_GUIDANCE if blocked else [])


def build_plan(device_type: str, observations: list[Observation], reviews: list[ObservationReview]) -> FunctionalPlan:
    safety = safety_state(observations, reviews)
    checks = [] if safety.blocked else CHECKS[device_type]
    return FunctionalPlan(device_type=device_type, safety=safety, checks=checks, guidance=[] if safety.blocked else CHECK_GUIDANCE)


def evaluate(
    device_type: str,
    observations: list[Observation],
    reviews: list[ObservationReview],
    responses: list[CheckResponse],
) -> FunctionalEvaluation:
    safety = safety_state(observations, reviews)
    checks = CHECKS[device_type]
    if safety.blocked:
        return FunctionalEvaluation(
            outcomes=[CheckOutcome(check_id=c.id, label=c.label, status="blocked_by_safety", note="") for c in checks],
            clarifications=[],
            conditional_findings=["Functional state is unknown: checks were stopped because of a suspected safety risk."],
            complete=False,
            blocked_by_safety=True,
        )

    answers = {r.check_id: r for r in responses}
    power = answers.get(POWER_CHECK)
    power_answer = power.answer if power else None
    outcomes, clarifications, findings = [], [], []

    for c in checks:
        r = answers.get(c.id)
        answer = r.answer if r else None
        note = r.note.strip()[:500] if r else ""
        if c.depends_on_power and power_answer == "fail":
            status = "unavailable_power_failed"
            if answer == "pass":
                clarifications.append(
                    f"{c.label} was reported as Pass, but the device did not power on. Please re-check the Power on answer."
                )
        elif answer is None:
            status = "not_answered"
        else:
            status = answer
            if c.depends_on_power and answer == "pass" and power_answer in ("unsure", "unable", None):
                clarifications.append(
                    f"{c.label} was reported as Pass, which needs the device to be on. Please update the Power on answer."
                )
        accessory = r.accessory_check if r and c.id == "charging" else None
        outcomes.append(CheckOutcome(check_id=c.id, label=c.label, status=status, note=note, accessory_check=accessory))

    status_of = {o.check_id: o.status for o in outcomes}
    if status_of.get("display") == "fail" and status_of.get("touch") == "pass":
        clarifications.append("Touch was reported working while the display failed. How did you confirm touch?")

    for o in outcomes:
        if o.status in ("unsure", "unable", "not_answered"):
            findings.append(f"{o.label}: unknown ({o.status.replace('_', ' ')}). Treated as unknown, not as working.")
    if status_of.get(POWER_CHECK) == "fail":
        findings.append(
            "The device did not power on. Causes range from an empty or worn battery to a charger or board fault; "
            "this alone does not mean recycling is the best option."
        )
    if status_of.get("charging") == "fail":
        findings.append(
            "Charging failed. Possible causes include the charger or cable, the charging port, the battery or internal "
            "circuitry. This is not a confirmed part failure."
        )
    for item in resolve_observations(observations, reviews):
        obs = item.observation
        if item.state != "withdrawn" and obs.kind == "physical_damage" and any(
            w in obs.part.lower() for w in ("glass", "screen", "display")
        ):
            if status_of.get("touch") == "pass" or status_of.get("display") == "pass":
                findings.append(
                    f"{obs.part}: visible damage is recorded and the display/touch were reported working. Both are true."
                )

    complete = all(o.status in ("pass", "fail") for o in outcomes)
    return FunctionalEvaluation(
        outcomes=outcomes,
        clarifications=clarifications,
        conditional_findings=findings,
        complete=complete and not clarifications,
        blocked_by_safety=False,
    )
