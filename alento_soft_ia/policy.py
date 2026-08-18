"""Políticas conservadoras por domínio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Set


@dataclass(frozen=True)
class DomainPolicy:
    name: str
    allowed_tools: Set[str]
    human_approval_required: bool
    can_write_external_system: bool


POLICIES = {
    "general": DomainPolicy(
        name="general",
        allowed_tools={"read_workspace", "write_workspace"},
        human_approval_required=False,
        can_write_external_system=False,
    ),
    "engineering": DomainPolicy(
        name="engineering",
        allowed_tools={"read_workspace", "write_workspace"},
        human_approval_required=True,
        can_write_external_system=False,
    ),
    "clinical": DomainPolicy(
        name="clinical",
        allowed_tools={"read_workspace", "write_workspace"},
        human_approval_required=True,
        can_write_external_system=False,
    ),
    "hr": DomainPolicy(
        name="hr",
        allowed_tools={"read_workspace", "write_workspace"},
        human_approval_required=True,
        can_write_external_system=False,
    ),
    "finance": DomainPolicy(
        name="finance",
        allowed_tools={"read_workspace", "write_workspace"},
        human_approval_required=True,
        can_write_external_system=False,
    ),
}


def get_policy(domain: str) -> DomainPolicy:
    return POLICIES.get(domain, POLICIES["general"])
