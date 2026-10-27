from typing import Literal

from pydantic import BaseModel

DeviceType = Literal["laptop", "mobile"]

# "simulated" = mock fixture, never real evidence. "live" = returned by a real provider.
ResultSource = Literal["simulated", "live"]

IssueCode = Literal[
    "timeout",
    "quota",
    "auth",
    "invalid_response",
    "budget_limit",
    "not_configured",
    "provider_error",
]


class ProviderIssue(BaseModel):
    """A provider problem reported to the user instead of fabricated results."""

    step: str
    code: IssueCode
    message: str


class Money(BaseModel):
    min: float
    max: float
    currency: str
