#!/usr/bin/env python3
"""
Brownfield onboarding demo.

Points the governance interrogation at a small sample portfolio of existing repos,
one already conformant, the others carrying typical gaps. Shows the survey gate on a
single repo, then fans onboarding across the whole portfolio and prints per-repo
conformance plus a portfolio rollup.

    python3 examples/run_onboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.gates import GatePause
from pipeline.governance import ESSENTIAL_IGNORES, RepoSnapshot
from pipeline.onboard import onboard_portfolio, onboard_repo
from pipeline.telemetry import ListRecorder


SAMPLE_PORTFOLIO = [
    # A repo that already meets the standard.
    RepoSnapshot(
        name="a-mcp-runmeter",
        has_readme=True, has_license=True, has_ci=True, has_onboarding=True,
        has_architecture=True, has_agent_context=True, registered=True,
        default_branch_protected=True, gitignore_patterns=set(ESSENTIAL_IGNORES),
    ),
    # An inherited service with several gaps.
    RepoSnapshot(
        name="legacy-billing-service",
        has_readme=True, has_license=False, has_ci=False, has_onboarding=False,
        has_architecture=False, registered=False, default_branch_protected=False,
        gitignore_patterns={"__pycache__/"},
    ),
    # A prototype with a committed secret (a blocker).
    RepoSnapshot(
        name="quick-poc-integration",
        has_readme=True, has_license=False, has_ci=False, tracks_secrets=True,
        registered=False, gitignore_patterns=set(),
    ),
]


def main() -> int:
    recorder = ListRecorder()

    # 1) Single repo hits the survey gate, then proceeds once confirmed.
    target = SAMPLE_PORTFOLIO[1]
    print(f"Onboarding {target.name} (unconfirmed):")
    try:
        onboard_repo(target, recorder=recorder, survey_confirmed=False)
    except GatePause as pause:
        print(f"  survey gate: {pause.prompt}")
        print(f"  interrogation found score {pause.payload['score']} with gaps: "
              f"{', '.join(pause.payload['gaps'])}")
    result = onboard_repo(target, recorder=recorder, survey_confirmed=True)
    print(f"  confirmed. remediation plan ({len(result.plan)} items):")
    for item in result.plan:
        print(f"    [{item.severity:7}] {item.title}: {item.action}")

    # 2) Fan onboarding across the whole portfolio (batch confirmed).
    print("\nPortfolio onboarding:")
    results, summary = onboard_portfolio(SAMPLE_PORTFOLIO, recorder=recorder)
    for r in results:
        state = "conformant" if r.report.conformant else f"{len(r.report.failing)} gap(s)"
        print(f"  {r.repo:26} score {r.report.score:<5} {state}")
    print(f"\n  {summary.conformant}/{summary.total} conformant, "
          f"avg score {summary.avg_score}, {summary.nonconformant} need work.")
    print(f"  telemetry: {len(recorder.runs)} interrogation calls recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
