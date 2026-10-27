"""Live Google Places API (New) provider: Text Search only.

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
Location bias and regionCode do not strictly filter by country, so results are
also filtered on the address country code.
"""

import httpx

from ..config import Settings
from ..services.usage_tracking import BudgetExceeded, UsageTracker
from .errors import ProviderError

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PRO_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.addressComponents",
    "places.location",
    "places.googleMapsUri",
    "places.businessStatus",
]
ENTERPRISE_FIELDS = ["places.nationalPhoneNumber", "places.websiteUri"]
BIAS_RADIUS_M = 15000.0


def map_http_error(status: int, body: str) -> tuple[ProviderError, bool]:
    if status in (401, 403):
        return ProviderError(
            "auth",
            "Google rejected the request. Check GOOGLE_MAPS_API_KEY, that Places API (New) is enabled, "
            "and that billing is active for the project.",
        ), False
    if status == 429:
        return ProviderError("quota", "Google Places quota or rate limit reached."), False
    if status >= 500:
        return ProviderError("provider_error", "Google Places is temporarily unavailable."), True
    return ProviderError("provider_error", f"Google Places rejected the request (HTTP {status})."), False


class GooglePlacesProvider:
    def __init__(self, settings: Settings, tracker: UsageTracker, client: httpx.Client | None = None):
        if not settings.google_maps_api_key and client is None:
            raise ProviderError(
                "not_configured",
                "Live service search needs GOOGLE_MAPS_API_KEY in backend/.env. Add the key and restart the backend.",
            )
        self.settings = settings
        self.tracker = tracker
        self.client = client or httpx.Client(timeout=settings.request_timeout_seconds)

    def _price_usd(self) -> float:
        s = self.settings
        per_1k = s.places_enterprise_usd_per_1k if s.places_include_contact_fields else s.places_pro_usd_per_1k
        return per_1k / 1000

    def text_search(
        self,
        assessment_id: str,
        query: str,
        country: str,
        latitude: float | None,
        longitude: float | None,
        page_size: int = 5,
    ) -> list[dict]:
        s = self.settings
        fields = PRO_FIELDS + (ENTERPRISE_FIELDS if s.places_include_contact_fields else [])
        body: dict = {"textQuery": query, "regionCode": country, "languageCode": "en", "pageSize": page_size}
        if latitude is not None and longitude is not None:
            body["locationBias"] = {
                "circle": {"center": {"latitude": latitude, "longitude": longitude}, "radius": BIAS_RADIUS_M}
            }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": s.google_maps_api_key,
            "X-Goog-FieldMask": ",".join(fields),
        }
        last_error: ProviderError | None = None
        for _attempt in range(s.max_retries + 1):
            try:
                reservation = self.tracker.reserve(assessment_id, "google_places", "text_search", self._price_usd())
            except BudgetExceeded as exc:
                raise ProviderError("budget_limit", str(exc)) from exc
            try:
                response = self.client.post(TEXT_SEARCH_URL, json=body, headers=headers)
            except httpx.TimeoutException:
                self.tracker.record(reservation, status="error:timeout", places_requests=1)
                last_error = ProviderError("timeout", "Google Places did not respond in time.")
                continue
            except httpx.HTTPError as exc:
                self.tracker.record(reservation, status="error:provider_error", places_requests=1)
                raise ProviderError("provider_error", "Could not reach Google Places.") from exc
            if response.status_code != 200:
                error, retryable = map_http_error(response.status_code, response.text)
                # Failed requests are recorded at the estimate; Google may not bill them.
                self.tracker.record(reservation, status=f"error:{error.code}", places_requests=1)
                last_error = error
                if retryable:
                    continue
                raise error
            self.tracker.record(reservation, status="ok", actual_usd=self._price_usd(), places_requests=1)
            try:
                return response.json().get("places", [])
            except ValueError as exc:
                raise ProviderError("invalid_response", "Google Places returned an unreadable response.") from exc
        raise last_error or ProviderError("provider_error", "Google Places request failed.")


def place_country(place: dict) -> str | None:
    for comp in place.get("addressComponents", []) or []:
        if "country" in comp.get("types", []):
            return (comp.get("shortText") or "").upper() or None
    return None


def create() -> GooglePlacesProvider:
    """Builds the live provider from settings. Tests replace this function."""
    from ..config import get_settings
    from ..services.usage_tracking import get_tracker

    return GooglePlacesProvider(get_settings(), get_tracker())
