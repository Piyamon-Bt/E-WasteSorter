from typing import Literal

from pydantic import BaseModel

from .common import DeviceType, Money
from .functional import FunctionalEvaluation
from .market import ConfirmedIdentity, PriceResearch, ServicesResult
from .physical import ObservationReview, PhysicalAssessment

Action = Literal["reuse", "resell_as_is", "repair_then_reuse", "repair_then_resell", "recycle"]


class LocationChoice(BaseModel):
    country: str
    area: str | None = None
    used_device_location: bool = False


class AssessmentSnapshot(BaseModel):
    """Everything the browser holds for one assessment. Never stored by the backend."""

    device_type: DeviceType
    physical: PhysicalAssessment
    reviews: list[ObservationReview] = []
    functional: FunctionalEvaluation | None = None
    identity: ConfirmedIdentity
    location: LocationChoice | None = None
    prices: PriceResearch | None = None
    services: ServicesResult | None = None


class ActionOption(BaseModel):
    action: Action
    title: str
    summary: str
    prerequisites: list[str]
    tradeoffs: list[str]
    uncertainty: list[str]
    gross_sale: Money | None
    repair_cost: Money | None
    net_proceeds: Money | None
    avoided_cost: Money | None
    financial_note: str


class Ranking(BaseModel):
    basis: Literal["financial_value", "resource_use"]
    order: list[Action]
    unranked: list[Action]
    explanation: list[str]
    complete: bool


class RecommendationResult(BaseModel):
    options: list[ActionOption]
    financial_ranking: Ranking
    resource_ranking: Ranking
    safety_constrained: bool
    conditional_findings: list[str]
    rankings_differ: str | None
    disclaimers: list[str]


class ReportRequest(BaseModel):
    snapshot: AssessmentSnapshot
    recommendation: RecommendationResult | None = None
