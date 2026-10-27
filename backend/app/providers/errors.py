from ..schemas.common import IssueCode, ProviderIssue


class ProviderError(Exception):
    """A provider call failed. Callers turn this into a visible issue, never into mock data."""

    def __init__(self, code: IssueCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_issue(self, step: str) -> ProviderIssue:
        return ProviderIssue(step=step, code=self.code, message=self.message)
