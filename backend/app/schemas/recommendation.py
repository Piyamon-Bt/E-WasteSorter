from typing import Literal

from pydantic import BaseModel

from .common import DeviceType, Money
from .functional import FunctionalEvaluation
from .market import ConfirmedIdentity, PriceResearch, PriceType, ServicesResult
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


class SaleChannelEstimate(BaseModel):
    """Price range from one sale channel for one device condition. Channels are never pooled."""

    price_type: PriceType
    device_state: str
    range: Money
    records: int
    used_for_calculation: bool


class ActionOption(BaseModel):
    action: Action
    title: str
    summary: str
    prerequisites: list[str]
    tradeoffs: list[str]
    uncertainty: list[str]
    sale_channels: list[SaleChannelEstimate] = []
    sale_basis: PriceType | None = None
    gross_sale: Money | None
    repair_cost: Money | None
    repair_cost_complete: bool = True
    net_proceeds: Money | None
    avoided_cost: Money | None
    # complete: every input is evidenced on a sale or buyback basis with a complete repair cost.
    # conditional: numbers exist but rest on asking prices, partial costs or unpriced causes.
    # insufficient: no usable numbers.
    financial_status: Literal["complete", "conditional", "insufficient"] = "insufficient"
    financial_note: str


class Ranking(BaseModel):
    basis: Literal["financial_value", "resource_use"]
    order: list[Action]
    # Options with numbers that rest on incomplete evidence; ordered by midpoint but not definitive.
    conditional: list[Action] = []
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
    # General guidance, shown separately from the ranked options.
    disposal_guidance: list[str] = []


class ReportRequest(BaseModel):
    snapshot: AssessmentSnapshot
    recommendation: RecommendationResult | None = None
