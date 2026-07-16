"""
Base domain exceptions. Module-specific exceptions (e.g. auth's
InvalidCredentialsError) subclass these. Controllers translate these into
HTTP responses — the domain/service layers never import FastAPI.
"""


class DomainError(Exception):
    """Base class for all domain-level errors across Sentinel modules."""


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state (e.g. duplicate)."""


class UnauthorizedError(DomainError):
    """Raised when authentication fails or credentials/tokens are invalid."""


class RateLimitExceededError(DomainError):
    """Raised when a caller exceeds an enforced rate limit."""
