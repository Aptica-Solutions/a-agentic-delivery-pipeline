"""
Telemetry recorders.

Every stage is an agent making model calls, so every stage can emit a run record.
The Recorder protocol keeps the pipeline decoupled from where telemetry lands:

- NullRecorder     -- default; drops records, so the pipeline runs anywhere.
- ListRecorder     -- keeps records in memory; handy for tests and demos.
- RunmeterRecorder -- forwards to the companion runmeter MCP server / library
                      (https://github.com/Aptica-Solutions/a-mcp-runmeter).

The RunmeterRecorder holds a callable rather than importing runmeter directly, so
this package has zero hard dependency on it. Wire in whatever transport you use
(MCP tool call, HTTP, direct import) by passing a record function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass
class RunRecord:
    stage: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    status: str = "ok"
    tags: list[str] = field(default_factory=list)


class Recorder(Protocol):
    def record(self, run: RunRecord) -> None: ...


class NullRecorder:
    """Default recorder: telemetry is a no-op."""

    def record(self, run: RunRecord) -> None:  # noqa: D401
        return None


class ListRecorder:
    """Collects records in memory. Useful for tests, demos, and quick rollups."""

    def __init__(self) -> None:
        self.runs: list[RunRecord] = []

    def record(self, run: RunRecord) -> None:
        self.runs.append(run)

    def total_by_stage(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.runs:
            out[r.stage] = out.get(r.stage, 0) + r.input_tokens + r.output_tokens
        return out


class RunmeterRecorder:
    """
    Forwards records to runmeter via an injected `record_fn`.

    `record_fn` receives a dict shaped like runmeter's `runmeter_record` input, e.g.
    {"model": ..., "input_tokens": ..., "output_tokens": ..., "latency_ms": ...,
     "status": ..., "agent": ..., "tags": [...]}. Supply an adapter that calls the
     runmeter MCP tool or library; this class never imports runmeter itself.
    """

    def __init__(self, record_fn: Callable[[dict[str, Any]], None]) -> None:
        self._record_fn = record_fn

    def record(self, run: RunRecord) -> None:
        self._record_fn(
            {
                "model": run.model,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "latency_ms": run.latency_ms,
                "status": run.status,
                "agent": run.stage,
                "tags": run.tags,
            }
        )
