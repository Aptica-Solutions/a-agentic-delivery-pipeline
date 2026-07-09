"""
Brownfield onboarding.

Point this at a repository (or a whole portfolio) you did not create. It interrogates
each repo against the governance standards, runs the onboarding survey, and, once a
human confirms at the survey gate, emits a conformance report and an ordered remediation
plan. This is the practical alternative to a big-bang standardization rewrite: one
human-checked conversation per repo, fanned across the fleet.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import model
from .gates import GatePause
from .governance import (
    ConformanceReport,
    RemediationItem,
    RepoSnapshot,
    audit_repo,
    remediation_plan,
)
from .profile import EngagementProfile
from .telemetry import NullRecorder, Recorder, RunRecord


@dataclass
class OnboardingResult:
    repo: str
    survey: dict
    report: ConformanceReport
    plan: list[RemediationItem]


def _meter(recorder: Recorder, result: model.ModelResult, tags: list[str]) -> None:
    recorder.record(
        RunRecord(
            stage="onboard",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            tags=tags,
        )
    )


def interrogate(snapshot: RepoSnapshot, *, recorder: Recorder | None = None) -> ConformanceReport:
    """Run the governance interrogation for one repo and return its conformance report."""
    recorder = recorder or NullRecorder()
    res = model.call(snapshot.name, purpose="governance-interrogate")
    _meter(recorder, res, tags=[snapshot.name, "governance"])
    return audit_repo(snapshot)


def onboard_repo(
    snapshot: RepoSnapshot,
    *,
    profile: EngagementProfile | None = None,
    recorder: Recorder | None = None,
    survey_confirmed: bool = False,
) -> OnboardingResult:
    """
    Onboard a single existing repo. Interrogation runs first; then the survey gate
    pauses (via GatePause) until a human confirms the inferred survey. Remediation is
    only planned after confirmation, so nothing is proposed behind the human's back.
    """
    profile = profile or EngagementProfile()
    report = interrogate(snapshot, recorder=recorder)

    if not survey_confirmed:
        raise GatePause(
            "survey-gate",
            f"Confirm the onboarding survey for {snapshot.name} before remediation.",
            payload={
                "repo": snapshot.name,
                "score": report.score,
                "gaps": [r.title for r in report.failing],
            },
        )

    survey = {
        "repo": snapshot.name,
        "profile": profile.name,
        "registered": snapshot.registered,
        "score": report.score,
    }
    return OnboardingResult(snapshot.name, survey, report, remediation_plan(report))


@dataclass
class PortfolioSummary:
    total: int
    conformant: int
    avg_score: float

    @property
    def nonconformant(self) -> int:
        return self.total - self.conformant


def onboard_portfolio(
    snapshots: list[RepoSnapshot],
    *,
    profile: EngagementProfile | None = None,
    recorder: Recorder | None = None,
    survey_confirmed: bool = True,
) -> tuple[list[OnboardingResult], PortfolioSummary]:
    """
    Fan onboarding across a portfolio. The registry accumulates a portfolio-wide view of
    what is and is not yet conformant. `survey_confirmed=True` represents a batch the
    human has approved; pass False to require per-repo confirmation at the survey gate.
    """
    results = [
        onboard_repo(s, profile=profile, recorder=recorder, survey_confirmed=survey_confirmed)
        for s in snapshots
    ]
    conformant = sum(1 for r in results if r.report.conformant)
    avg = round(sum(r.report.score for r in results) / len(results), 3) if results else 0.0
    return results, PortfolioSummary(len(results), conformant, avg)
