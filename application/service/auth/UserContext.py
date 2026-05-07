"""Immutable value object representing an authenticated user."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UserContext:
    user_id: str
    email: str
    display_name: str | None = None
