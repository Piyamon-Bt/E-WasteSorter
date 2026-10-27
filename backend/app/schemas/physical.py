from typing import Literal

from pydantic import BaseModel, Field

from .common import DeviceType, ResultSource

ObservationKind = Literal["cosmetic_wear", "physical_damage", "suspected_safety_risk", "unassessable"]
RiskType = Literal["swelling", "separation", "burning", "liquid_damage", "other"]
Uncertainty = Literal["low", "medium", "high"]
EvidenceStrength = Literal["none", "weak", "moderate", "strong"]
UserResponse = Literal["agree", "disagree", "unsure"]

# Required photo slots per device. Users assign each image to a slot; the
# prototype checks slot completion, not the actual camera angle.
REQUIRED_VIEWS: dict[str, dict[str, str]] = {
    "mobile": {
        "front": "Front screen",
        "back": "Back",
        "left": "Left edge",
        "right": "Right edge",
        "top": "Top edge",
        "bottom": "Bottom edge",
    },
    "laptop": {
        "screen": "Screen (lid open, powered off)",
        "keyboard": "Keyboard and touchpad",
        "lid": "Outer lid",
        "underside": "Underside",
        "left": "Left edge / ports",
        "right": "Right edge / ports",
    },
}
DETAIL_VIEW = "detail"  # optional extra close-ups or label photos


class Observation(BaseModel):
    id: str
    kind: ObservationKind
    part: str
    description: str
    views: list[str] = Field(description="Slot ids of the photos that support this observation")
    visible_evidence: str
    uncertainty: Uncertainty
    uncertainty_reason: str
    risk_type: RiskType | None = None


class IdentityCandidate(BaseModel):
    brand: str | None
    model: str | None
    evidence: str


class IdentitySuggestion(BaseModel):
    evidence_strength: EvidenceStrength
    candidates: list[IdentityCandidate]
    visible_specs: list[str]
    notes: str


class PhysicalAssessment(BaseModel):
    source: ResultSource
    model: str | None
    device_type: DeviceType
    observations: list[Observation]
    unassessable_areas: list[str]
    identity: IdentitySuggestion
    summary: str
    view_check: Literal["slot_assignment_only"] = "slot_assignment_only"


class ImageQualityIssue(BaseModel):
    view: str
    filename: str
    problem: str
    blocking: bool


class FollowUpResult(BaseModel):
    observation_id: str
    outcome: Literal["upheld", "revised", "not_supported", "unresolved"]
    revised_observation: Observation | None
    explanation: str
    extra_images: int
    source: ResultSource
    model: str | None


class ObservationReview(BaseModel):
    observation_id: str
    response: UserResponse | None = None
    note: str = ""
    # Every follow-up result for this observation, oldest first. Kept so a risk found by an
    # earlier re-check can never be lost when a later re-check returns a different result.
    follow_ups: list[FollowUpResult] = []

    @property
    def latest_follow_up(self) -> FollowUpResult | None:
        return self.follow_ups[-1] if self.follow_ups else None
