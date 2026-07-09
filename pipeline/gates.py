"""
Human-in-the-loop gates.

The pipeline structures and routes; a human decides. A stage raises GatePause to
hand control back for a decision (analyst answers, QA sign-off, change approval).
The orchestrator catches it, surfaces the pending questions, and resumes when the
human's response is supplied. Nothing reaches production on autopilot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class GatePause(Exception):
    """Raised by a stage to pause the pipeline for a human decision."""

    def __init__(self, gate: str, prompt: str, payload: Any = None) -> None:
        super().__init__(f"{gate}: {prompt}")
        self.gate = gate
        self.prompt = prompt
        self.payload = payload


@dataclass
class HumanResponse:
    """A human's answer to a paused gate, supplied on resume."""

    gate: str
    data: dict[str, Any] = field(default_factory=dict)
