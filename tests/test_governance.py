"""
Tests for the brownfield governance interrogation and onboarding.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.gates import GatePause
from pipeline.governance import (
    ESSENTIAL_IGNORES,
    RepoSnapshot,
    audit_repo,
    remediation_plan,
)
from pipeline.onboard import onboard_portfolio, onboard_repo
from pipeline.telemetry import ListRecorder


def _clean_repo(name="clean"):
    return RepoSnapshot(
        name=name, has_readme=True, has_license=True, has_ci=True, has_onboarding=True,
        has_architecture=True, has_agent_context=True, registered=True,
        default_branch_protected=True, gitignore_patterns=set(ESSENTIAL_IGNORES),
    )


def test_clean_repo_is_conformant():
    report = audit_repo(_clean_repo())
    assert report.conformant
    assert report.score == 1.0
    assert report.failing == []


def test_gaps_are_detected_and_scored():
    snap = RepoSnapshot(name="gappy", has_readme=True, gitignore_patterns={"__pycache__/"})
    report = audit_repo(snap)
    assert not report.conformant
    ids = {r.id for r in report.failing}
    assert {"license", "ci", "registered", "onboarding"} <= ids
    # README passes; ignore hygiene is partial (drift), so score is between 0 and 1.
    assert 0.0 < report.score < 1.0
    hygiene = next(r for r in report.results if r.id == "ignore-hygiene")
    assert hygiene.status == "drift"


def test_committed_secret_is_a_blocker_and_leads_the_plan():
    snap = RepoSnapshot(name="leaky", has_readme=True, tracks_secrets=True)
    plan = remediation_plan(audit_repo(snap))
    assert plan[0].id == "no-secrets"
    assert plan[0].severity == "blocker"
    # Plan is ordered by severity: no descending severity after the first.
    order = [ {"blocker":0,"high":1,"medium":2,"low":3}[i.severity] for i in plan ]
    assert order == sorted(order)


def test_onboard_repo_pauses_at_survey_gate():
    snap = RepoSnapshot(name="x", has_readme=True)
    with pytest.raises(GatePause) as exc:
        onboard_repo(snap, survey_confirmed=False)
    assert exc.value.gate == "survey-gate"
    assert "gaps" in exc.value.payload


def test_onboard_repo_returns_result_once_confirmed():
    snap = RepoSnapshot(name="x", has_readme=True)
    result = onboard_repo(snap, survey_confirmed=True)
    assert result.repo == "x"
    assert result.survey["repo"] == "x"
    assert len(result.plan) == len(result.report.failing)


def test_portfolio_rollup_counts_and_averages():
    portfolio = [_clean_repo("a"), RepoSnapshot(name="b", has_readme=True), _clean_repo("c")]
    rec = ListRecorder()
    results, summary = onboard_portfolio(portfolio, recorder=rec)
    assert summary.total == 3
    assert summary.conformant == 2
    assert summary.nonconformant == 1
    assert 0.0 < summary.avg_score < 1.0
    assert len(rec.runs) == 3  # one interrogation per repo


def test_interrogation_emits_telemetry():
    rec = ListRecorder()
    onboard_repo(_clean_repo(), recorder=rec, survey_confirmed=True)
    assert len(rec.runs) == 1
    assert rec.runs[0].stage == "onboard"
    assert "governance" in rec.runs[0].tags


def test_code_and_registry_checklist_agree():
    """The example registry's checklist.yaml must list the same standards as the code."""
    import re

    from pipeline.governance import DEFAULT_STANDARDS

    checklist = Path(__file__).resolve().parents[1] / "examples" / "governance-registry" / "standards" / "checklist.yaml"

    # Parse per item, skipping comment lines, so header comments do not pollute the match.
    yaml_sev: dict[str, str] = {}
    current: str | None = None
    for line in checklist.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        m_id = re.match(r"-\s*id:\s*([a-z0-9-]+)", stripped)
        if m_id:
            current = m_id.group(1)
            continue
        m_sev = re.match(r"severity:\s*([a-z]+)", stripped)
        if m_sev and current:
            yaml_sev[current] = m_sev.group(1)

    code_sev = {s.id: s.severity for s in DEFAULT_STANDARDS}
    assert set(yaml_sev) == set(code_sev), "checklist.yaml and DEFAULT_STANDARDS have drifted"
    assert yaml_sev == code_sev, "severities drifted between registry and code"
