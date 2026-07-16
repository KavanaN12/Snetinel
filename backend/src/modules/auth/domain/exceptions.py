"""
Auth-specific domain exceptions. Subclass shared base exceptions so generic
handlers (if any) still catch them, while controllers can also match on the
specific type for precise HTTP status mapping.
"""
from src.shared.domain.exceptions import ConflictError, UnauthorizedError


class InvalidCredentialsError(UnauthorizedError):
    """
    Raised for both 'no such user' and 'wrong password'. Deliberately
    generic — distinguishing the two at the API boundary is a user
    enumeration vulnerability.
    """


class UserAlreadyExistsError(ConflictError):
    """Raised on registration when the email is already taken."""


class TokenRevokedError(UnauthorizedError):
    """Raised when a refresh token has been explicitly revoked (logout)."""


class TokenNotFoundError(UnauthorizedError):
    """Raised when a presented refresh token doesn't match any stored hash."""
