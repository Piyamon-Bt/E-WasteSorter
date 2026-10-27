from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import DeviceType, ProviderIssue, ResultSource

PriceType = Literal[
    "asking_price",  # active listing
    "completed_sale",  # only with evidence that the sale completed
    "buyback_offer",  # published shop/trade-in offer
    "part_price",  # part only, no labor
    "repair_labor",  # labor only
    "repair_quote",  # combined part + labor
]
DeviceState = Literal["working", "damaged_or_faulty", "any", "not_applicable"]
PartQuality = Literal["genuine", "aftermarket", "unknown", "not_applicable"]
ServiceCategory = Literal["repair", "buyback", "recycling"]


class ConfirmedIdentity(BaseModel):
    """Identity as confirmed by the user. Separate from what the photos prove."""

    status: Literal["confirmed", "candidate_selected", "unknown"]
    brand: str | None = None
    model: str | None = None
    variant: str | None = None
    storage: str | None = None
    ram: str | None = None
    evidence_verified: bool = False

    def label(self) -> str:
        if self.status == "unknown":
            return "Unknown model"
        parts = [self.brand, self.model, self.variant, self.storage, self.ram]
        return " ".join(p for p in parts if p) or "Unknown model"


class RepairScenario(BaseModel):
    """One possible repair intervention, never a confirmed diagnosis.

    `needs` lists every finding this intervention might address. One intervention
    that appears under several needs is priced once. Different scenarios listed
    under the same need are alternative causes.
    """

    id: str
    needs: list[str]
    title: str
    description: str


class PriceRecord(BaseModel):
    price_type: PriceType
    item: str
    amount_min: float
    amount_max: float
    currency: str
    market: str = Field(description="ISO 3166-1 alpha-2 country code")
    device_state: DeviceState
    part_quality: PartQuality
    scenario_id: str | None
    source_url: str
    source_title: str
    retrieved_at: datetime
    match_level: Literal["exact", "close", "indicative"]
    matching_conditions: str
    limitations: str
    simulated: bool


class ChannelStatus(BaseModel):
    price_type: PriceType
    status: Literal["found", "insufficient_data", "not_searched"]
    note: str


class PriceRequest(BaseModel):
    device_type: DeviceType
    identity: ConfirmedIdentity
    country: str = Field(min_length=2, max_length=2)
    area: str | None = None
    condition_summary: list[str] = []
    damaged_parts: list[str] = []
    failed_checks: list[str] = []
    # True when charging failed with a charger the user knows works (accessory ruled out).
    accessory_ruled_out: bool = False


class PriceResearch(BaseModel):
    source: ResultSource
    model: str | None
    country: str
    identity_label: str
    status: Literal["complete", "partial", "insufficient_data", "skipped_unknown_identity", "failed"]
    retrieved_at: datetime
    records: list[PriceRecord]
    channels: list[ChannelStatus]
    repair_scenarios: list[RepairScenario]
    issues: list[ProviderIssue]
    dropped_records: int = 0
    notes: list[str] = []


class ServicesRequest(BaseModel):
    device_type: DeviceType
    country: str = Field(min_length=2, max_length=2)
    area: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    needs: list[ServiceCategory] = ["repair", "buyback", "recycling"]


class LocalService(BaseModel):
    name: str
    category: ServiceCategory
    address: str | None
    phone: str | None
    website: str | None
    maps_url: str | None
    place_id: str | None
    business_status: str | None
    distance_km: float | None
    distance_kind: Literal["straight_line"] | None
    relevance: str
    simulated: bool


class ServicesResult(BaseModel):
    source: ResultSource
    country: str
    area_label: str
    retrieved_at: datetime
    services: list[LocalService]
    issues: list[ProviderIssue]
    attribution: str
    notes: list[str] = []
