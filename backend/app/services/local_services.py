"""Nearby repair, buyback and recycling services (discovery only).

The app never contacts, books or sends photos to any business.
"""

from datetime import datetime, timezone

from ..config import Settings
from ..providers import google_places_provider, mock_provider
from ..providers.errors import ProviderError
from ..schemas.market import LocalService, ServicesRequest, ServicesResult

DEVICE_WORD = {"mobile": "mobile phone", "laptop": "laptop"}
QUERIES = {
    "repair": "{device} repair shop",
    "buyback": "used {device} buyback",
    "recycling": "electronic waste recycling",
}
RELEVANCE = {
    "repair": "Matched a search for {device} repair. A listing does not prove it can fix this fault.",
    "buyback": "Matched a search for used {device} buyback. Offers are not confirmed.",
    "recycling": "Matched a search for e-waste recycling. Check which devices it accepts.",
}
ATTRIBUTION = "Place data from Google Maps."


def find(settings: Settings, assessment_id: str, req: ServicesRequest, scenario: str | None) -> ServicesResult:
    req = req.model_copy(update={"country": req.country.upper()})
    has_coords = req.latitude is not None and req.longitude is not None
    area_label = req.area or ("Current location" if has_coords else req.country)
    if not req.area and not has_coords:
        return ServicesResult(
            source="simulated" if settings.is_mock else "live", country=req.country, area_label=area_label,
            retrieved_at=datetime.now(timezone.utc), services=[], issues=[], attribution="",
            notes=["Enter an area or use your current location to search for nearby services."],
        )

    if settings.is_mock:
        try:
            return mock_provider.find_services(req, mock_provider.resolve_scenario(scenario))
        except ProviderError as exc:
            return _failed(req, area_label, "simulated", exc)

    try:
        provider = google_places_provider.create()
    except ProviderError as exc:
        return _failed(req, area_label, "live", exc)

    device = DEVICE_WORD[req.device_type]
    services: list[LocalService] = []
    issues = []
    dropped = 0
    seen: set[str] = set()
    for category in req.needs:
        query = QUERIES[category].format(device=device)
        if req.area:
            query += f" in {req.area}"
        try:
            places = provider.text_search(assessment_id, query, req.country, req.latitude, req.longitude)
        except ProviderError as exc:
            issues.append(exc.to_issue(f"services_{category}"))
            if exc.code in ("budget_limit", "auth", "quota"):
                break
            continue
        for place in places:
            pid = place.get("id")
            if pid in seen:
                continue
            country = google_places_provider.place_country(place)
            if country and country != req.country:
                dropped += 1  # location bias is not a strict country filter
                continue
            seen.add(pid)
            loc = place.get("location") or {}
            distance = None
            if has_coords and "latitude" in loc and "longitude" in loc:
                distance = round(mock_provider.haversine_km(req.latitude, req.longitude, loc["latitude"], loc["longitude"]), 1)
            services.append(LocalService(
                name=(place.get("displayName") or {}).get("text", "Unnamed place"),
                category=category,
                address=place.get("formattedAddress"),
                phone=place.get("nationalPhoneNumber"),
                website=place.get("websiteUri"),
                maps_url=place.get("googleMapsUri"),
                place_id=pid,
                business_status=place.get("businessStatus"),
                distance_km=distance,
                distance_kind="straight_line" if distance is not None else None,
                relevance=RELEVANCE[category].format(device=device),
                simulated=False,
            ))
    notes = ["Distances are straight-line, not travel distance."] if has_coords else ["No distances: location coordinates were not provided."]
    notes.append("Listings do not prove certification, current opening hours or fault-specific repair capability.")
    if dropped:
        notes.append(f"{dropped} result(s) outside the selected country were removed.")
    return ServicesResult(
        source="live", country=req.country, area_label=area_label, retrieved_at=datetime.now(timezone.utc),
        services=services, issues=issues, attribution=ATTRIBUTION, notes=notes,
    )


def _failed(req: ServicesRequest, area_label: str, source: str, exc: ProviderError) -> ServicesResult:
    return ServicesResult(
        source=source, country=req.country, area_label=area_label, retrieved_at=datetime.now(timezone.utc),
        services=[], issues=[exc.to_issue("local_services")], attribution="",
        notes=["Service search failed. The rest of the assessment is still valid."],
    )
