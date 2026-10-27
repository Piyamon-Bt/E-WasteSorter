"""Live-mode behavior with fake provider clients. No real network or paid calls."""

import json
from types import SimpleNamespace

import httpx
import openai
import pytest
from conftest import HEADERS, upload

from app.providers import google_places_provider, openai_provider
from app.providers.errors import ProviderError
from app.providers.google_places_provider import GooglePlacesProvider
from app.providers.openai_provider import OpenAIProvider
from app.schemas.market import ConfirmedIdentity, PriceRequest, ServicesRequest
from app.services import local_services, price_research
from app.services.usage_tracking import get_tracker

REQ = httpx.Request("POST", "https://api.openai.com/v1/responses")
KNOWN = ConfirmedIdentity(status="confirmed", brand="Brand", model="Model 1")


class FakeResponses:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def _go(self, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    parse = _go
    create = _go


def fake_openai(monkeypatch, settings, result=None, error=None):
    fake = FakeResponses(result, error)
    provider = OpenAIProvider(settings, get_tracker(), client=SimpleNamespace(responses=fake))
    monkeypatch.setattr(openai_provider, "create", lambda: provider)
    return fake


def price_response(records, cited):
    text = json.dumps({"records": records, "notes": []})
    message = SimpleNamespace(type="message", content=[SimpleNamespace(
        type="output_text", text=text, annotations=[SimpleNamespace(type="url_citation", url=u) for u in cited])])
    search = SimpleNamespace(type="web_search_call", action=SimpleNamespace(sources=[]))
    return SimpleNamespace(output=[search, message], output_text=text,
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


def rec(url, market="TH", currency="THB"):
    return {"price_type": "asking_price", "item": "Used", "amount_min": 100, "amount_max": 200, "currency": currency,
            "market": market, "device_state": "working", "part_quality": "not_applicable", "scenario_id": None,
            "source_url": url, "source_title": "Shop", "match_level": "exact", "matching_conditions": "same model",
            "limitations": "asking price"}


def test_live_without_keys_gives_actionable_error_not_mock(configure):
    from fastapi.testclient import TestClient

    from app.main import app

    configure(app_mode="live")
    client = TestClient(app)
    data, files = upload("mobile")
    r = client.post("/api/assessments/physical", data=data, files=files, headers=HEADERS)
    assert r.status_code == 503
    assert "OPENAI_API_KEY" in r.json()["detail"]["message"]

    prices = client.post("/api/market/prices", headers=HEADERS, json={
        "device_type": "mobile", "identity": KNOWN.model_dump(), "country": "TH"}).json()
    assert prices["status"] == "failed" and prices["records"] == []
    assert prices["source"] == "live"
    assert prices["issues"][0]["code"] == "not_configured"

    services = client.post("/api/services/nearby", headers=HEADERS, json={
        "device_type": "mobile", "country": "TH", "area": "Bangkok"}).json()
    assert services["services"] == [] and services["issues"][0]["code"] == "not_configured"


def test_mock_mode_never_builds_live_providers(client, configure, monkeypatch):
    def boom():
        raise AssertionError("live provider used in mock mode")

    monkeypatch.setattr(openai_provider, "create", boom)
    monkeypatch.setattr(google_places_provider, "create", boom)
    data, files = upload("laptop")
    assert client.post("/api/assessments/physical", data=data, files=files, headers=HEADERS).status_code == 200
    client.post("/api/market/prices", headers=HEADERS, json={"device_type": "laptop", "identity": KNOWN.model_dump(), "country": "TH"})
    client.post("/api/services/nearby", headers=HEADERS, json={"device_type": "laptop", "country": "TH", "area": "Bangkok"})
    assert not get_tracker().path.exists()  # no paid usage recorded
    assert get_tracker().summary()["estimated_spent_thb"] == 0


@pytest.mark.parametrize(
    "error, code",
    [
        (openai.APITimeoutError(request=REQ), "timeout"),
        (openai.RateLimitError("insufficient_quota", response=httpx.Response(429, request=REQ), body=None), "quota"),
        (openai.AuthenticationError("bad key", response=httpx.Response(401, request=REQ), body=None), "auth"),
    ],
)
def test_price_research_provider_errors_are_reported(configure, monkeypatch, error, code):
    settings = configure(app_mode="live", openai_api_key="sk-test")
    fake_openai(monkeypatch, settings, error=error)
    result = price_research.research(settings, "a" * 16, PriceRequest(device_type="mobile", identity=KNOWN, country="TH"), None)
    assert result.status == "failed"
    assert result.records == []
    assert result.issues[0].code == code


def test_timeouts_are_retried_within_budget(configure, monkeypatch):
    settings = configure(app_mode="live", openai_api_key="sk-test", max_retries=2)
    fake = fake_openai(monkeypatch, settings, error=openai.APITimeoutError(request=REQ))
    price_research.research(settings, "a" * 16, PriceRequest(device_type="mobile", identity=KNOWN, country="TH"), None)
    assert fake.calls == 3
    lines = get_tracker().path.read_text().splitlines()
    assert len(lines) == 3  # each attempt is recorded at its worst-case estimate
    assert all(json.loads(line)["cost_basis"] == "worst_case_estimate" for line in lines)


def test_invalid_response_is_reported(configure, monkeypatch):
    settings = configure(app_mode="live", openai_api_key="sk-test")
    bad = SimpleNamespace(output=[], output_text="no json here", usage=SimpleNamespace(input_tokens=10, output_tokens=5))
    fake_openai(monkeypatch, settings, result=bad)
    result = price_research.research(settings, "a" * 16, PriceRequest(device_type="mobile", identity=KNOWN, country="TH"), None)
    assert result.status == "failed" and result.issues[0].code == "invalid_response"


def test_uncited_foreign_or_wrong_currency_records_are_dropped(configure, monkeypatch):
    settings = configure(app_mode="live", openai_api_key="sk-test")
    response = price_response(
        [rec("https://shop.example.th/item/1"), rec("https://made-up.example/2"),
         rec("https://shop.example.th/item/3", market="US"), rec("https://shop.example.th/item/4", currency="USD")],
        cited=["https://shop.example.th/item/1", "https://shop.example.th/item/3", "https://shop.example.th/item/4"],
    )
    fake_openai(monkeypatch, settings, result=response)
    result = price_research.research(settings, "a" * 16, PriceRequest(device_type="mobile", identity=KNOWN, country="TH"), None)
    assert [r.source_url for r in result.records] == ["https://shop.example.th/item/1"]
    assert result.dropped_records == 3
    assert result.records[0].simulated is False
    entry = json.loads(get_tracker().path.read_text().splitlines()[0])
    assert entry["cost_basis"] == "reported_usage" and entry["web_search_calls"] == 1
    assert "Used" not in json.dumps(entry)  # ledger holds no content


def test_physical_live_timeout_returns_http_error(configure, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    settings = configure(app_mode="live", openai_api_key="sk-test")
    fake_openai(monkeypatch, settings, error=openai.APITimeoutError(request=REQ))
    data, files = upload("mobile")
    r = TestClient(app).post("/api/assessments/physical", data=data, files=files, headers=HEADERS)
    assert r.status_code == 504
    assert r.json()["detail"]["issue"]["code"] == "timeout"


def test_budget_limit_stops_calls_before_spending(configure, monkeypatch):
    settings = configure(app_mode="live", openai_api_key="sk-test", project_budget_thb=1, prior_spend_thb=0.99)
    fake = fake_openai(monkeypatch, settings, result=price_response([], []))
    result = price_research.research(settings, "a" * 16, PriceRequest(device_type="mobile", identity=KNOWN, country="TH"), None)
    assert result.issues[0].code == "budget_limit"
    assert fake.calls == 0


def test_per_assessment_call_limit(configure, monkeypatch):
    settings = configure(app_mode="live", openai_api_key="sk-test", max_calls_per_assessment=1)
    fake = fake_openai(monkeypatch, settings, result=price_response([], []))
    req = PriceRequest(device_type="mobile", identity=KNOWN, country="TH")
    price_research.research(settings, "a" * 16, req, None)
    second = price_research.research(settings, "a" * 16, req, None)
    assert fake.calls == 1
    assert second.issues[0].code == "budget_limit"
    # A different assessment has its own counter.
    price_research.research(settings, "b" * 16, req, None)
    assert fake.calls == 2


def test_places_results_are_filtered_by_country(configure, monkeypatch):
    settings = configure(app_mode="live", google_maps_api_key="g-test")

    def handler(request: httpx.Request):
        assert request.headers["X-Goog-FieldMask"].startswith("places.id")
        return httpx.Response(200, json={"places": [
            {"id": "1", "displayName": {"text": "Local Fix"}, "formattedAddress": "Bangkok",
             "addressComponents": [{"types": ["country"], "shortText": "TH"}],
             "location": {"latitude": 13.76, "longitude": 100.51}, "googleMapsUri": "https://maps.google.com/?cid=1"},
            {"id": "2", "displayName": {"text": "Far Away"}, "addressComponents": [{"types": ["country"], "shortText": "MY"}]},
        ]})

    provider = GooglePlacesProvider(settings, get_tracker(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(google_places_provider, "create", lambda: provider)
    result = local_services.find(settings, "a" * 16, ServicesRequest(device_type="mobile", country="TH", latitude=13.75, longitude=100.5, needs=["repair"]), None)
    assert [s.name for s in result.services] == ["Local Fix"]
    assert result.services[0].distance_kind == "straight_line"
    assert result.attribution


def test_places_auth_error_is_reported(configure, monkeypatch):
    settings = configure(app_mode="live", google_maps_api_key="g-test")
    transport = httpx.MockTransport(lambda r: httpx.Response(403, json={"error": {}}))
    provider = GooglePlacesProvider(settings, get_tracker(), client=httpx.Client(transport=transport))
    monkeypatch.setattr(google_places_provider, "create", lambda: provider)
    result = local_services.find(settings, "a" * 16, ServicesRequest(device_type="mobile", country="TH", area="Bangkok"), None)
    assert result.services == [] and result.issues[0].code == "auth"
    assert len(result.issues) == 1  # stops after an auth error instead of repeating it


def test_missing_key_provider_raises_not_configured(configure):
    settings = configure(app_mode="live")
    with pytest.raises(ProviderError) as exc:
        OpenAIProvider(settings, get_tracker())
    assert exc.value.code == "not_configured"
