"""
Shared pipeline context.

Threaded through every stage: the artifact bag, the engagement profile, the telemetry
recorder, and any human responses supplied on resume. Lives in its own module so both
the stages and the orchestrator can import it without a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .gates import HumanResponse
from .model import ModelResult
from .profile import EngagementProfile
from .telemetry import NullRecorder, Recorder, RunRecord


@dataclass
class Context:
    profile: EngagementProfile = field(default_factory=EngagementProfile)
    recorder: Recorder = field(default_factory=NullRecorder)
    bag: dict[str, Any] = field(default_factory=dict)
    responses: dict[str, HumanResponse] = field(default_factory=dict)

    def get(self, name: str) -> Any:
        if name not in self.bag:
            raise KeyError(
                f"Artifact {name!r} is not in the bag yet. Upstream stage did not run "
                f"or did not produce it. Present: {sorted(self.bag)}."
            )
        return self.bag[name]

    def put(self, name: str, artifact: Any) -> None:
        self.bag[name] = artifact

    def meter(self, stage: str, result: ModelResult, tags: list[str]) -> None:
        """Record a stage's model call as telemetry."""
        self.recorder.record(
            RunRecord(
                stage=stage,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                tags=tags,
            )
        )
