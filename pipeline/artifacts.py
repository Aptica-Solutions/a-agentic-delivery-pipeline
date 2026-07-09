"""
Typed artifacts that flow between pipeline stages.

Each stage consumes some artifacts and produces others, exactly as documented in
docs/pipeline-stages.md. Keeping them as explicit dataclasses (rather than loose
dicts) is what makes the contracts real: a stage cannot silently drop a field the
next stage depends on. All fields are vendor-neutral.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Requirement:
    """The raw incoming request, from any channel."""

    summary: str
    source: str = "freeform"  # e.g. email, ticket, message, doc
    artifact_id: Optional[str] = None  # registry id once matched
    body: str = ""


@dataclass
class OpenQuestion:
    id: str
    text: str
    answer: Optional[str] = None

    @property
    def resolved(self) -> bool:
        return self.answer is not None


@dataclass
class TaskEntry:
    """Stage 1 output: a registered task plus ready-to-run setup steps."""

    artifact_id: str
    title: str
    setup_steps: list[str] = field(default_factory=list)
    work_items: list[str] = field(default_factory=list)


@dataclass
class Architecture:
    """Stage 2 output: a versioned design with open questions and a scaffold seed."""

    artifact_id: str
    summary: str
    integration_map: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    open_questions: list[OpenQuestion] = field(default_factory=list)
    version: int = 1
    changelog: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """True when no open question is still unanswered."""
        return all(q.resolved for q in self.open_questions)


@dataclass
class ScaffoldSeed:
    """Byproduct of stage 2, consumed by stage 3. Fields carry confidence levels."""

    project_name: str
    language_stack: str
    fields: dict[str, str] = field(default_factory=dict)
    confidence: dict[str, str] = field(default_factory=dict)  # field -> high|medium|low


@dataclass
class Repo:
    """Stage 3 output: the scaffolded repository and its onboarding surface."""

    name: str
    template: str
    onboarding_complete: bool = False
    setup_commands: list[str] = field(default_factory=list)


@dataclass
class CoverageItem:
    requirement: str
    state: str  # covered | partial | gap


@dataclass
class CoverageReport:
    """Stage 4 output: requirements traceability for the active branch."""

    items: list[CoverageItem] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return all(i.state == "covered" for i in self.items)

    @property
    def gaps(self) -> list[CoverageItem]:
        return [i for i in self.items if i.state != "covered"]


@dataclass
class Defect:
    id: str
    description: str
    resolved: bool = False


@dataclass
class QAHandoff:
    """Stage 5 output on sign-off, consumed by stage 6."""

    artifact_id: str
    defects: list[Defect] = field(default_factory=list)
    acceptance_passed: bool = False


@dataclass
class ChangeRequest:
    """Stage 6 output, routed by stage 7."""

    artifact_id: str
    summary: str
    approved: bool = False
    approver: Optional[str] = None


@dataclass
class DocSet:
    """Stage 8 output: formatted deliverables and where they were published."""

    published_to: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    fmt: str = "markdown"
