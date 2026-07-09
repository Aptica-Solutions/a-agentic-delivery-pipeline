"""
Engagement profile: config over code.

A profile declares the tools and gates for a given context. Stages read the profile
and adapt, so the same stage code serves every engagement. A gate set to a falsey
value is skipped cleanly rather than special-cased in the stage logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EngagementProfile:
    """
    Declarative configuration for one engagement.

    ticketing_system / work_tracking / docs_targets are abstract tool categories,
    never a specific vendor. change_gate controls whether stage 7 blocks on approval.
    """

    name: str = "default"
    ticketing_system: str = "generic-itsm"
    work_tracking: str = "generic-tracker"
    docs_targets: list[str] = field(default_factory=lambda: ["docs-platform"])
    doc_format: str = "markdown"
    change_gate: str = "approval"  # "approval" | "none"
    approver: Optional[str] = "release-manager"
    template: str = "enterprise-template"

    @property
    def change_gate_enabled(self) -> bool:
        return self.change_gate == "approval"

    @classmethod
    def from_file(cls, path: str | Path) -> "EngagementProfile":
        data = json.loads(Path(path).read_text())
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "EngagementProfile":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
