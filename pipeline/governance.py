"""
Governance interrogation.

Scores an existing repository against a standards checklist and turns the gaps into
an ordered remediation plan. This is the engine behind the brownfield path: point it
at tech you inherited, and it tells you where the repo drifts from the enterprise
standard and the smallest set of changes to bring it into conformance.

The checklist here mirrors the kind of standards a governance registry enforces
(README, license, CI, onboarding/architecture docs, ignore hygiene, no committed
secrets, registry membership, branch protection). It is data, not hard-coded logic:
swap in your own Standard list to match your registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# Lower sorts first, so blockers lead the remediation plan.
SEVERITY_ORDER = {"blocker": 0, "high": 1, "medium": 2, "low": 3}

# The build/env/cache patterns a healthy .gitignore should cover.
ESSENTIAL_IGNORES = {"__pycache__/", ".env", ".venv/", "node_modules/", "dist/", "build/"}


@dataclass
class RepoSnapshot:
    """Observable state of an existing repo, as an interrogation would gather it."""

    name: str
    has_readme: bool = False
    has_license: bool = False
    has_ci: bool = False
    has_onboarding: bool = False
    has_architecture: bool = False
    has_agent_context: bool = False  # AGENTS.md / CLAUDE.md / copilot-instructions
    gitignore_patterns: set[str] = field(default_factory=set)
    tracks_secrets: bool = False  # True means a secret is committed (a blocker)
    registered: bool = False  # present in the governance registry
    default_branch_protected: bool = False


def _ignore_check(s: RepoSnapshot) -> str:
    if not s.gitignore_patterns:
        return "missing"
    covered = ESSENTIAL_IGNORES & s.gitignore_patterns
    if covered == ESSENTIAL_IGNORES:
        return "pass"
    return "drift" if covered else "missing"


@dataclass
class Standard:
    id: str
    title: str
    severity: str  # blocker | high | medium | low
    remediation: str
    check: Callable[[RepoSnapshot], str]  # returns pass | drift | missing


DEFAULT_STANDARDS: list[Standard] = [
    Standard("no-secrets", "No committed secrets", "blocker",
             "Remove committed secrets, ignore .env, and rotate any exposed keys.",
             lambda s: "missing" if s.tracks_secrets else "pass"),
    Standard("license", "License present", "high",
             "Add a LICENSE (MIT for internal/prototype assets).",
             lambda s: "pass" if s.has_license else "missing"),
    Standard("ci", "CI workflow present", "high",
             "Add .github/workflows/ci.yml running lint and tests.",
             lambda s: "pass" if s.has_ci else "missing"),
    Standard("registered", "Registered in governance", "high",
             "Add a registry entry so the repo is tracked and scaffolding-aware.",
             lambda s: "pass" if s.registered else "missing"),
    Standard("branch-protection", "Default branch protected", "high",
             "Apply the production-tier ruleset (PR review, no force-push, no deletion).",
             lambda s: "pass" if s.default_branch_protected else "missing"),
    Standard("readme", "README present", "medium",
             "Add a README describing purpose, setup, and usage.",
             lambda s: "pass" if s.has_readme else "missing"),
    Standard("onboarding", "Onboarding doc present", "medium",
             "Generate ONBOARDING.md via the onboarding survey.",
             lambda s: "pass" if s.has_onboarding else "missing"),
    Standard("architecture", "Architecture doc present", "medium",
             "Capture the design in ARCHITECTURE.md.",
             lambda s: "pass" if s.has_architecture else "missing"),
    Standard("ignore-hygiene", "Ignore hygiene", "medium",
             "Extend .gitignore to cover build, env, and cache artifacts.",
             _ignore_check),
    Standard("agent-context", "Agent context file present", "low",
             "Add AGENTS.md / CLAUDE.md so assistants have project context.",
             lambda s: "pass" if s.has_agent_context else "missing"),
]


@dataclass
class CheckResult:
    id: str
    title: str
    severity: str
    status: str  # pass | drift | missing


@dataclass
class ConformanceReport:
    repo: str
    results: list[CheckResult]

    @property
    def score(self) -> float:
        """Weighted conformance 0.0-1.0 (pass=1, drift=0.5, missing=0)."""
        if not self.results:
            return 0.0
        weight = {"pass": 1.0, "drift": 0.5, "missing": 0.0}
        return round(sum(weight[r.status] for r in self.results) / len(self.results), 3)

    @property
    def conformant(self) -> bool:
        return all(r.status == "pass" for r in self.results)

    @property
    def failing(self) -> list[CheckResult]:
        return [r for r in self.results if r.status != "pass"]


@dataclass
class RemediationItem:
    id: str
    title: str
    severity: str
    action: str
    status: str  # the failing status that triggered this item


def audit_repo(snapshot: RepoSnapshot, standards: list[Standard] = DEFAULT_STANDARDS) -> ConformanceReport:
    """Score a repo snapshot against the standards."""
    results = [CheckResult(st.id, st.title, st.severity, st.check(snapshot)) for st in standards]
    return ConformanceReport(snapshot.name, results)


def remediation_plan(report: ConformanceReport, standards: list[Standard] = DEFAULT_STANDARDS) -> list[RemediationItem]:
    """Ordered fixes for every failing check, blockers first."""
    by_id = {st.id: st for st in standards}
    items = [
        RemediationItem(r.id, r.title, r.severity, by_id[r.id].remediation, r.status)
        for r in report.failing
    ]
    items.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 99))
    return items
