"""
Agentic delivery pipeline: a minimal, genericized reference implementation.

Carries a raw requirement through eight stages to a governed, documented solution,
threading a typed artifact bag stage to stage, pausing at human-in-the-loop gates,
and emitting per-stage telemetry. Model calls are deterministic stubs so the whole
pipeline runs with no external services or credentials; the stub is the seam where
a real model client drops in.
"""

from .artifacts import (
    Architecture,
    ChangeRequest,
    CoverageReport,
    DocSet,
    QAHandoff,
    Requirement,
    ScaffoldSeed,
    TaskEntry,
)
from .governance import (
    ConformanceReport,
    RemediationItem,
    RepoSnapshot,
    Standard,
    audit_repo,
    remediation_plan,
)
from .onboard import OnboardingResult, PortfolioSummary, onboard_portfolio, onboard_repo
from .orchestrator import Pipeline, PipelinePaused, StageResult
from .profile import EngagementProfile
from .telemetry import NullRecorder, Recorder, RunmeterRecorder

__all__ = [
    "Requirement",
    "TaskEntry",
    "Architecture",
    "ScaffoldSeed",
    "CoverageReport",
    "QAHandoff",
    "ChangeRequest",
    "DocSet",
    "EngagementProfile",
    "Pipeline",
    "PipelinePaused",
    "StageResult",
    "Recorder",
    "NullRecorder",
    "RunmeterRecorder",
    "RepoSnapshot",
    "Standard",
    "ConformanceReport",
    "RemediationItem",
    "audit_repo",
    "remediation_plan",
    "onboard_repo",
    "onboard_portfolio",
    "OnboardingResult",
    "PortfolioSummary",
]

__version__ = "0.1.0"
