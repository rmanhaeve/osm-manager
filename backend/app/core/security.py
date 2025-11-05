from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Principal:
    username: str
    roles: list[str]


def get_current_principal() -> Principal:
    """Placeholder for RBAC integration (OIDC, OAuth, etc.)."""
    return Principal(username="system", roles=["admin"])
