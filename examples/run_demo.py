#!/usr/bin/env python3
"""
End-to-end demo.

Runs a raw requirement through the whole pipeline, answering each human gate as it
comes up, and prints a per-stage telemetry rollup at the end. No credentials, no
network: the model stub makes every run deterministic.

    python3 examples/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.artifacts import Requirement
from pipeline.gates import HumanResponse
from pipeline.orchestrator import Pipeline, PipelinePaused
from pipeline.profile import EngagementProfile
from pipeline.telemetry import ListRecorder


# Canned human answers, keyed by gate. In a real run these come from a person.
ANSWERS = {
    "analyst-qa": HumanResponse("analyst-qa", {"answers": {"Q1": "Daily batch."}}),
    "qa-signoff": HumanResponse("qa-signoff", {"passed": True}),
    "change-approval": HumanResponse(
        "change-approval", {"approved": True, "approver": "release-manager"}
    ),
}


def main() -> int:
    recorder = ListRecorder()
    pipeline = Pipeline(profile=EngagementProfile(), recorder=recorder)
    pipeline.start(
        Requirement(
            summary="Automate the weekly provider roster reconciliation",
            source="ticket",
            artifact_id="ART-2092",
        )
    )

    # Drive the pipeline, answering each gate as it pauses.
    while True:
        try:
            ctx = pipeline.run()
            break
        except PipelinePaused as pause:
            print(f"  gate reached: {pause.stage} -> {pause.gate}: {pause.prompt}")
            response = ANSWERS.get(pause.gate)
            if response is None:
                print(f"  no canned answer for {pause.gate}; stopping.")
                return 1
            pipeline.resume(response)

    print("\nStage history:")
    for h in pipeline.history:
        print(f"  {h.stage:14} {h.status}")

    docs = ctx.get("docs")
    cr = ctx.get("change_request")
    print(f"\nOutcome: change {'APPROVED' if cr.approved else 'pending'} "
          f"by {cr.approver}; docs published to {', '.join(docs.published_to)}.")

    print("\nTelemetry (tokens by stage):")
    for stage, tokens in recorder.total_by_stage().items():
        print(f"  {stage:14} {tokens:>6} tokens")
    total = sum(r.input_tokens + r.output_tokens for r in recorder.runs)
    print(f"  {'TOTAL':14} {total:>6} tokens across {len(recorder.runs)} model calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
