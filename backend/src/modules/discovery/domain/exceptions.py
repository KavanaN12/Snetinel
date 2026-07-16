"""Discovery-specific domain exceptions."""

from src.shared.domain.exceptions import NotFoundError, UnauthorizedError


class DiscoveryRunNotFoundError(NotFoundError):
    """Raised when a discovery run cannot be found."""


class DiscoveryAccessDeniedError(UnauthorizedError):
    """Raised when a user cannot access a discovery run."""
