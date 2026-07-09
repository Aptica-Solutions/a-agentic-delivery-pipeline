"""
Orchestrator.

Runs the stages in order, threading the artifact bag through each. When a stage
raises GatePause, the pipeline stops at that stage and returns control with the
pending prompt. Supply the human's response and call resume() to continue from the
same stage, so gates behave as real checkpoints rather than fire-and-forget calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .artifacts import Requirement
from .context import Context
from .gates import GatePause, HumanResponse
from .profile import EngagementProfile
from .stages import DEFAULT_STAGES, Stage
from .telemetry import NullRecorder, Recorder


@dataclass
class StageResult:
    stage: str
    status: str  # "ran" | "paused"


class PipelinePaused(Exception):
    """Raised by run()/resume() when a human gate is reached."""

    def __init__(self, gate: str, stage: str, prompt: str, payload: object) -> None:
        super().__init__(f"paused at {stage} gate {gate!r}: {prompt}")
        self.gate = gate
        self.stage = stage
        self.prompt = prompt
        self.payload = payload


@dataclass
class Pipeline:
    profile: EngagementProfile = field(default_factory=EngagementProfile)
    recorder: Recorder = field(default_factory=NullRecorder)
    stages: list[Stage] = field(default_factory=lambda: list(DEFAULT_STAGES))

    _ctx: Context = field(init=False, repr=False)
    _cursor: int = field(default=0, init=False, repr=False)
    history: list[StageResult] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._ctx = Context(profile=self.profile, recorder=self.recorder)

    @property
    def context(self) -> Context:
        return self._ctx

    def start(self, requirement: Requirement) -> "Pipeline":
        self._ctx.put("requirement", requirement)
        self._cursor = 0
        self.history.clear()
        return self

    def run(self) -> Context:
        """Run from the current cursor to completion, or until a gate pauses."""
        while self._cursor < len(self.stages):
            stage = self.stages[self._cursor]
            try:
                stage.run(self._ctx)
            except GatePause as pause:
                self.history.append(StageResult(stage.name, "paused"))
                raise PipelinePaused(
                    pause.gate, stage.name, pause.prompt, pause.payload
                ) from None
            self.history.append(StageResult(stage.name, "ran"))
            self._cursor += 1
        return self._ctx

    def resume(self, response: HumanResponse) -> "Pipeline":
        """
        Record a human decision for the paused gate. The next run() call re-runs the
        paused stage (idempotent on resume) with the response available. Injecting and
        running are kept separate so a driver loop only ever needs to catch PipelinePaused
        around run().
        """
        self._ctx.responses[response.gate] = response
        return self

    @property
    def done(self) -> bool:
        return self._cursor >= len(self.stages)
