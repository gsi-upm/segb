"""Backward-compatible aliases for security helpers."""

from ..core.security import Role, User, validate_token

__all__ = ["Role", "User", "validate_token"]
