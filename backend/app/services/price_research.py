"""Local-market price research with provenance checks.

Prices are only searched in the selected country. Unknown identity skips
model-specific prices. Provider failures become visible issues.
"""

from datetime import datetime, timezone

from ..config import Settings
from ..providers import mock_provider, openai_provider
from ..providers.errors import ProviderError
from ..schemas.market import ChannelStatus, PriceRequest, PriceResearch
from .recommendations import derive_repair_scenarios

ALL_TYPES = ("asking_price", "completed_sale", "buyback_offer", "part_price", "repair_labor", "repair_quote")

# Local currency per country for currency checks. Countries not listed are
# accepted with any currency the source states, as long as the market matches.
COUNTRY_CURRENCY = {
    "TH": "THB", "US": "USD", "GB": "GBP", "JP": "JPY", "SG": "SGD", "MY": "MYR", "VN": "VND",
    "ID": "IDR", "PH": "PHP", "AU": "AUD", "NZ": "NZD", "CA": "CAD", "IN": "INR", "KR": "KRW",
    "CN": "CNY", "HK": "HKD", "TW": "TWD", "DE": "EUR", "FR": "EUR", "NL": "EUR", "IT": "EUR", "ES": "EUR",
}


def _empty(req: PriceRequest, settings: Settings, status: str, source: str, model: str | None) -> PriceResearch:
    return PriceResearch(
        source=source,
        model=model,
        country=req.country.upper(),
        identity_label=req.identity.label(),
        status=status,
        retrieved_at=datetime.now(timezone.utc),
        records=[],
        channels=[ChannelStatus(price_type=t, status="not_searched", note="") for t in ALL_TYPES],
        repair_scenarios=derive_repair_scenarios(req.device_type, req.damaged_parts, req.failed_checks, req.accessory_ruled_out),
        issues=[],
    )


def research(settings: Settings, assessment_id: str, req: PriceRequest, scenario: str | None) -> PriceResearch:
    req = req.model_copy(update={"country": req.country.upper()})
    source = "simulated" if settings.is_mock else "live"
    model = mock_provider.MOCK_MODEL if settings.is_mock else settings.openai_model
    scenarios = derive_repair_scenarios(req.device_type, req.damaged_parts, req.failed_checks, req.accessory_ruled_out)

    if req.identity.status == "unknown":
        result = _empty(req, settings, "skipped_unknown_identity", source, model)
        result.notes.append(
            "Model unknown: model-specific device and part prices were not searched. "
            "General findings and local services are still available."
        )
        return result

    try:
        if settings.is_mock:
            return mock_provider.research_prices(req, scenarios, mock_provider.resolve_scenario(scenario))
        provider = openai_provider.create()
        records, notes, dropped = provider.research_prices(
            assessment_id, req, scenarios, COUNTRY_CURRENCY.get(req.country)
        )
    except ProviderError as exc:
        result = _empty(req, settings, "failed", source, model)
        result.issues.append(exc.to_issue("price_research"))
        result.notes.append("Price research failed. The rest of the assessment is still valid.")
        return result

    found = {r.price_type for r in records}
    result = _empty(req, settings, "complete" if records else "insufficient_data", source, model)
    result.records = records
    result.dropped_records = dropped
    result.notes = notes[:10]
    result.channels = [
        ChannelStatus(
            price_type=t,
            status="found" if t in found else "insufficient_data",
            note="" if t in found else "No local evidence found for this price type.",
        )
        for t in ALL_TYPES
    ]
    if dropped:
        result.notes.append(
            f"{dropped} result(s) were discarded because their source was not a cited page, "
            "or their market or currency did not match the selected country."
        )
    if not records:
        result.notes.append("No local price evidence found. Prices from other countries are not substituted.")
    return result
