"""Workspace-specific domain exceptions."""

from src.shared.domain.exceptions import NotFoundError, UnauthorizedError


class WorkspaceNotFoundError(NotFoundError):
    """Raised when a workspace cannot be found."""


class WorkspaceAccessDeniedError(UnauthorizedError):
    """Raised when a user is not the owner of a workspace."""
