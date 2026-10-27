"""Project-wide paid API usage tracking and budget protection.

The ledger is a local JSONL file with usage/cost metadata only: no images,
coordinates, prompts or findings. It survives restarts so the project budget is
tracked across assessments, while assessments themselves stay in memory.

All costs here are estimates from configured pricing. They are not billed
amounts, and usage made outside this app is unknown unless you set
PRIOR_SPEND_THB.
"""

import hashlib
import json
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

from ..config import Settings, get_settings

MAX_TRACKED_ASSESSMENTS = 500


class BudgetExceeded(Exception):
    """Raised before a paid call when a project or per-assessment limit would be exceeded."""


@dataclass
class Reservation:
    id: str
    assessment_ref: str
    provider: str
    operation: str
    model: str | None
    estimated_usd: float
    estimated_tokens: int


def _assessment_ref(assessment_id: str) -> str:
    # A one-way reference so the ledger can group calls without storing the id itself.
    return hashlib.sha256(assessment_id.encode()).hexdigest()[:12]


class UsageTracker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.usage_ledger_path
        self._lock = threading.Lock()
        self._reserved_thb = 0.0
        self._per_assessment: OrderedDict[str, dict[str, int]] = OrderedDict()
        self._spent_thb = self._load_spent()

    def _load_spent(self) -> float:
        if not self.path.exists():
            return 0.0
        total = 0.0
        for line in self.path.read_text().splitlines():
            if line.strip():
                total += float(json.loads(line).get("estimated_cost_thb", 0.0))
        return total

    def _counters(self, ref: str) -> dict[str, int]:
        counters = self._per_assessment.setdefault(ref, {"calls": 0, "tokens": 0})
        self._per_assessment.move_to_end(ref)
        while len(self._per_assessment) > MAX_TRACKED_ASSESSMENTS:
            self._per_assessment.popitem(last=False)
        return counters

    def remaining_thb(self) -> float:
        s = self.settings
        return s.project_budget_thb - s.prior_spend_thb - self._spent_thb - self._reserved_thb

    def reserve(
        self,
        assessment_id: str,
        provider: str,
        operation: str,
        estimated_usd: float,
        estimated_tokens: int = 0,
        model: str | None = None,
    ) -> Reservation:
        """Reserve a worst-case estimate before a paid call. Every retry needs its own reservation."""
        s = self.settings
        estimated_thb = estimated_usd * s.usd_to_thb
        ref = _assessment_ref(assessment_id)
        with self._lock:
            counters = self._counters(ref)
            if counters["calls"] >= s.max_calls_per_assessment:
                raise BudgetExceeded(
                    f"This assessment reached its limit of {s.max_calls_per_assessment} paid API calls."
                )
            if counters["tokens"] + estimated_tokens > s.max_tokens_per_assessment:
                raise BudgetExceeded(
                    f"This assessment would exceed its limit of {s.max_tokens_per_assessment:,} tokens."
                )
            if estimated_thb > self.remaining_thb():
                raise BudgetExceeded(
                    f"The remaining project budget (about THB {max(self.remaining_thb(), 0):,.2f}) "
                    f"is below this call's worst-case estimate (THB {estimated_thb:,.2f})."
                )
            counters["calls"] += 1
            counters["tokens"] += estimated_tokens
            self._reserved_thb += estimated_thb
        return Reservation(uuid.uuid4().hex, ref, provider, operation, model, estimated_usd, estimated_tokens)

    def record(
        self,
        reservation: Reservation,
        status: str,
        actual_usd: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        web_search_calls: int = 0,
        places_requests: int = 0,
    ) -> dict:
        """Release the reservation and append a ledger entry.

        When the provider did not report usage (errors, timeouts), the worst-case
        estimate is recorded, because the request may still have been billed.
        """
        s = self.settings
        cost_usd = actual_usd if actual_usd is not None else reservation.estimated_usd
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": reservation.provider,
            "operation": reservation.operation,
            "model": reservation.model,
            "status": status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "web_search_calls": web_search_calls,
            "places_requests": places_requests,
            "estimated_cost_usd": round(cost_usd, 6),
            "estimated_cost_thb": round(cost_usd * s.usd_to_thb, 4),
            "cost_basis": "reported_usage" if actual_usd is not None else "worst_case_estimate",
            "assessment_ref": reservation.assessment_ref,
        }
        with self._lock:
            self._reserved_thb = max(0.0, self._reserved_thb - reservation.estimated_usd * s.usd_to_thb)
            if input_tokens is not None and output_tokens is not None:
                counters = self._counters(reservation.assessment_ref)
                counters["tokens"] += input_tokens + output_tokens - reservation.estimated_tokens
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            self._spent_thb += entry["estimated_cost_thb"]
        return entry

    def summary(self) -> dict:
        s = self.settings
        entries = 0
        if self.path.exists():
            entries = sum(1 for line in self.path.read_text().splitlines() if line.strip())
        return {
            "project_budget_thb": s.project_budget_thb,
            "prior_spend_thb": s.prior_spend_thb,
            "estimated_spent_thb": round(self._spent_thb, 2),
            "remaining_thb": round(self.remaining_thb(), 2),
            "ledger_entries": entries,
            "usd_to_thb_assumption": s.usd_to_thb,
            "note": (
                "Estimates from configured pricing, not billed amounts. Usage outside this app "
                "is unknown unless entered as PRIOR_SPEND_THB. Check your provider billing pages."
            ),
        }


@lru_cache
def get_tracker() -> UsageTracker:
    return UsageTracker(get_settings())
