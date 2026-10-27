import json

import pytest

from app.config import get_settings
from app.services.usage_tracking import BudgetExceeded, UsageTracker


def test_ledger_persists_across_restarts_and_holds_metadata_only(configure):
    configure(project_budget_thb=100, usd_to_thb=35)
    settings = get_settings()
    tracker = UsageTracker(settings)
    res = tracker.reserve("assessment-xyz-123", "openai", "physical_assessment", 0.1, 1000, "m")
    tracker.record(res, "ok", actual_usd=0.05, input_tokens=800, output_tokens=100)

    restarted = UsageTracker(settings)  # e.g. after a backend restart or a page reload
    assert restarted.summary()["estimated_spent_thb"] == pytest.approx(1.75)
    entry = json.loads(settings.usage_ledger_path.read_text())
    assert "assessment-xyz-123" not in json.dumps(entry)
    assert set(entry) >= {"timestamp", "provider", "operation", "estimated_cost_thb", "cost_basis"}


def test_reservations_count_against_budget_for_concurrent_calls(configure):
    configure(project_budget_thb=10, usd_to_thb=10)
    tracker = UsageTracker(get_settings())
    tracker.reserve("a" * 16, "openai", "x", 0.6)  # THB 6 in flight
    with pytest.raises(BudgetExceeded):
        tracker.reserve("b" * 16, "openai", "x", 0.6)


def test_prior_spend_reduces_remaining_budget(configure):
    configure(project_budget_thb=4000, prior_spend_thb=3999)
    tracker = UsageTracker(get_settings())
    assert tracker.remaining_thb() == pytest.approx(1)
    with pytest.raises(BudgetExceeded):
        tracker.reserve("a" * 16, "openai", "x", 1.0)


def test_health_exposes_readiness_without_secrets(client, configure):
    configure(google_maps_api_key="secret-google-key", openai_api_key="sk-secret")
    body = client.get("/api/health").json()
    text = json.dumps(body)
    assert "secret" not in text
    assert body["openai"]["key_configured"] is True
    assert body["openai"]["connection_verified"] is False


def test_backend_stores_no_assessment_state(client):
    from app.main import app

    # The API has no endpoint that lists or returns earlier assessments.
    paths = set(app.openapi()["paths"])
    assert "/api/assessments/physical" in paths
    assert not any("history" in p or p.endswith("/assessments") for p in paths)
