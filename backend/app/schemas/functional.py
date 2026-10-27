from typing import Literal

from pydantic import BaseModel

from .common import DeviceType
from .physical import Observation, ObservationReview

CheckAnswer = Literal["pass", "fail", "unsure", "unable"]
CheckStatus = Literal[
    "pass",
    "fail",
    "unsure",
    "unable",
    "not_answered",
    "unavailable_power_failed",
    "blocked_by_safety",
]


class RiskStatus(BaseModel):
    observation_id: str
    part: str
    status: Literal["confirmed_by_user", "unresolved", "cleared_after_follow_up"]
    explanation: str


class SafetyState(BaseModel):
    blocked: bool
    risks: list[RiskStatus]
    guidance: list[str]


class CheckDefinition(BaseModel):
    id: str
    label: str
    instructions: str
    depends_on_power: bool


class FunctionalPlan(BaseModel):
    device_type: DeviceType
    safety: SafetyState
    checks: list[CheckDefinition]
    guidance: list[str]


class PlanRequest(BaseModel):
    device_type: DeviceType
    observations: list[Observation]
    reviews: list[ObservationReview]


class CheckResponse(BaseModel):
    check_id: str
    answer: CheckAnswer | None = None
    note: str = ""


class EvaluateRequest(BaseModel):
    device_type: DeviceType
    observations: list[Observation]
    reviews: list[ObservationReview]
    responses: list[CheckResponse]


class CheckOutcome(BaseModel):
    check_id: str
    label: str
    status: CheckStatus
    note: str


class FunctionalEvaluation(BaseModel):
    outcomes: list[CheckOutcome]
    clarifications: list[str]
    conditional_findings: list[str]
    complete: bool
    blocked_by_safety: bool
    disclaimer: str = "Function results are user-reported, not remotely verified hardware measurements."
