"""
Tests for the reference pipeline.

Covers the artifact flow end to end, each human gate's pause/resume behavior, the
defects and analyst loops, profile-driven gate skipping, and telemetry capture.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.artifacts import Requirement
from pipeline.gates import HumanResponse
from pipeline.orchestrator import Pipeline, PipelinePaused
from pipeline.profile import EngagementProfile
from pipeline.telemetry import ListRecorder


def _req():
    return Requirement(summary="Automate roster reconciliation", source="ticket", artifact_id="ART-1")


def _drive(pipeline, answers):
    """Run to completion, answering gates from the given dict."""
    while True:
        try:
            return pipeline.run()
        except PipelinePaused as pause:
            pipeline.resume(answers[pause.gate])


def _run_until_gate(pipeline, answers, stop_gate):
    """Answer earlier gates but return the PipelinePaused for stop_gate."""
    while True:
        try:
            pipeline.run()
            return None  # completed without hitting stop_gate
        except PipelinePaused as pause:
            if pause.gate == stop_gate:
                return pause
            pipeline.resume(answers[pause.gate])


ALL_ANSWERS = {
    "analyst-qa": HumanResponse("analyst-qa", {"answers": {"Q1": "Daily batch."}}),
    "qa-signoff": HumanResponse("qa-signoff", {"passed": True}),
    "change-approval": HumanResponse("change-approval", {"approved": True, "approver": "rm"}),
}


def test_full_run_reaches_docs_and_approval():
    p = Pipeline(recorder=ListRecorder()).start(_req())
    ctx = _drive(p, ALL_ANSWERS)
    assert p.done
    assert ctx.get("change_request").approved is True
    assert ctx.get("docs").published_to == ["docs-platform"]
    assert [h.stage for h in p.history if h.status == "ran"][-1] == "publish-docs"


def test_architect_pauses_for_analyst_then_resumes():
    p = Pipeline().start(_req())
    with pytest.raises(PipelinePaused) as exc:
        p.run()
    assert exc.value.gate == "analyst-qa"
    assert exc.value.stage == "architect"
    # Resume injects the answer; driving forward re-runs architect clean and versioned up.
    ctx = _drive(p, ALL_ANSWERS)
    arch = ctx.get("architecture")
    assert arch.clean
    assert arch.version == 2 and arch.changelog


def test_change_gate_blocks_without_approval():
    p = Pipeline().start(_req())
    pause = _run_until_gate(p, ALL_ANSWERS, stop_gate="change-approval")
    assert pause is not None and pause.gate == "change-approval"
    assert not p.done
    # A declined approval keeps the pipeline halted; it does not reach docs.
    assert "docs" not in p.context.bag


def test_profile_can_disable_change_gate():
    prof = EngagementProfile(change_gate="none")
    answers = {k: v for k, v in ALL_ANSWERS.items() if k != "change-approval"}
    p = Pipeline(profile=prof).start(_req())
    ctx = _drive(p, answers)  # no change-approval gate should ever fire
    assert p.done
    cr = ctx.get("change_request")
    assert cr.approved and "gate disabled" in cr.approver


def test_qa_defects_resolved_on_signoff():
    p = Pipeline().start(_req())
    ctx = _drive(p, ALL_ANSWERS)
    handoff = ctx.get("qa")
    assert handoff.acceptance_passed
    assert all(d.resolved for d in handoff.defects)


def test_telemetry_records_every_stage():
    rec = ListRecorder()
    p = Pipeline(recorder=rec).start(_req())
    _drive(p, ALL_ANSWERS)
    stages = {r.stage for r in rec.runs}
    # All eight stages emit at least one record.
    assert stages == {
        "intake", "architect", "scaffold", "develop",
        "qa", "qa-complete", "change-gate", "publish-docs",
    }
    assert all(r.input_tokens > 0 for r in rec.runs)


def test_coverage_is_clean_after_develop():
    p = Pipeline().start(_req())
    ctx = _drive(p, ALL_ANSWERS)
    assert ctx.get("coverage").clean


def test_missing_artifact_raises_clear_error():
    from pipeline.context import Context
    from pipeline.stages import ArchitectStage

    ctx = Context()
    with pytest.raises(KeyError) as exc:
        ArchitectStage().run(ctx)  # no requirement/task in the bag
    assert "not in the bag" in str(exc.value)


def test_deterministic_model_stub_is_stable():
    from pipeline import model

    a = model.call("same prompt", purpose="architect")
    b = model.call("same prompt", purpose="architect")
    assert (a.output_tokens, a.latency_ms) == (b.output_tokens, b.latency_ms)
