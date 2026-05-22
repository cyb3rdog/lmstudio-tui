class LMStudioError(Exception):
    """Base error for all LM Studio client errors."""


class ConnectionError(LMStudioError):
    """Server is unreachable."""


class AuthError(LMStudioError):
    """Authentication failed (401/403)."""


class APIError(LMStudioError):
    """Unexpected HTTP error from the server."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code


class TimeoutError(LMStudioError):
    """Request timed out."""
