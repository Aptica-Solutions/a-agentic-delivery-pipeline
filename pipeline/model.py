"""
Deterministic model stub.

Stands in for a real LLM call so the pipeline runs with no key and no network, and
so tests are stable. `call()` returns a ModelResult with reproducible token counts
and latency derived from the input. This is the single seam where a real model
client (Anthropic, Azure OpenAI, open-source, etc.) drops in: implement the same
signature and hand it to the stages.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class ModelResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


def _stable_int(seed: str, lo: int, hi: int) -> int:
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def call(prompt: str, *, model: str = "stub-sonnet", purpose: str = "") -> ModelResult:
    """
    Deterministic stand-in for a model call.

    Token counts scale loosely with prompt length so telemetry rollups look realistic;
    latency is stable per (purpose, prompt) so tests do not flake.
    """
    seed = f"{purpose}:{prompt}"
    input_tokens = max(8, len(prompt) // 4)
    output_tokens = _stable_int(seed, 40, 600)
    latency_ms = float(_stable_int(seed, 200, 2600))
    return ModelResult(
        text=f"[{purpose or 'result'}] {prompt[:60]}",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
