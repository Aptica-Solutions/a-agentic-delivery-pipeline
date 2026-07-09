"""
The eight pipeline stages.

Each stage is a small class with a stable `name` and a `run(ctx)` method that reads
its inputs from the context bag, does its work (calling the model stub and metering
the call), and writes its outputs back. Stages that own a human gate raise GatePause
until the matching HumanResponse is present in ctx.responses, so the orchestrator can
pause and resume them. Contracts mirror docs/pipeline-stages.md.
"""

from __future__ import annotations

from typing import Protocol

from . import model
from .artifacts import (
    Architecture,
    ChangeRequest,
    CoverageItem,
    CoverageReport,
    Defect,
    DocSet,
    OpenQuestion,
    QAHandoff,
    Repo,
    Requirement,
    ScaffoldSeed,
    TaskEntry,
)
from .context import Context
from .gates import GatePause


class Stage(Protocol):
    name: str

    def run(self, ctx: Context) -> None: ...


class IntakeStage:
    name = "intake"

    def run(self, ctx: Context) -> None:
        req: Requirement = ctx.get("requirement")
        res = model.call(req.summary, purpose="intake")
        ctx.meter(self.name, res, tags=[req.artifact_id or "unregistered", "intake"])
        artifact_id = req.artifact_id or "ART-0001"
        ctx.put(
            "task",
            TaskEntry(
                artifact_id=artifact_id,
                title=req.summary,
                setup_steps=[
                    "clone repository",
                    "create feature branch",
                    "provision environment from profile",
                ],
                work_items=[f"{artifact_id}-EPIC", f"{artifact_id}-DISCOVERY"],
            ),
        )


class ArchitectStage:
    """Owns the analyst Q&A gate. Loops (via resume) until the design is clean."""

    name = "architect"

    def run(self, ctx: Context) -> None:
        req: Requirement = ctx.get("requirement")
        arch: Architecture = ctx.bag.get("architecture") or Architecture(
            artifact_id=(ctx.get("task").artifact_id),
            summary=f"Solution design for: {req.summary}",
            integration_map=["source system", "target system", "work-tracking system"],
            risk_flags=["data-handling review needed"],
            open_questions=[
                OpenQuestion("Q1", "Confirm the integration cadence (batch or event)."),
            ],
        )

        # Resume mode: fold in analyst answers, resolve questions, bump the version.
        resp = ctx.responses.pop("analyst-qa", None)
        if resp is not None:
            answers: dict[str, str] = resp.data.get("answers", {})
            for q in arch.open_questions:
                if q.id in answers:
                    q.answer = answers[q.id]
            arch.version += 1
            arch.changelog.insert(
                0, f"v{arch.version} -- resolved {sorted(answers)}"
            )

        res = model.call(arch.summary, purpose="architect")
        ctx.meter(self.name, res, tags=[arch.artifact_id, "architect"])
        ctx.put("architecture", arch)

        if not arch.clean:
            pending = [q for q in arch.open_questions if not q.resolved]
            raise GatePause(
                "analyst-qa",
                "Open questions need analyst answers before the design is final.",
                payload=[{"id": q.id, "text": q.text} for q in pending],
            )

        # Byproduct: the scaffold seed for stage 3.
        ctx.put(
            "seed",
            ScaffoldSeed(
                project_name=_slug(req.summary),
                language_stack="python",
                fields={"artifact_id": arch.artifact_id},
                confidence={"project_name": "medium", "language_stack": "medium"},
            ),
        )


class ScaffoldStage:
    name = "scaffold"

    def run(self, ctx: Context) -> None:
        seed: ScaffoldSeed = ctx.get("seed")
        res = model.call(seed.project_name, purpose="scaffold")
        ctx.meter(self.name, res, tags=[seed.fields.get("artifact_id", "n/a"), "scaffold"])
        ctx.put(
            "repo",
            Repo(
                name=seed.project_name,
                template=ctx.profile.template,
                onboarding_complete=True,
                setup_commands=[
                    f"gh repo create {seed.project_name} --private --template {ctx.profile.template}",
                    "write ONBOARDING.md",
                    "write .env starter",
                ],
            ),
        )


class DevelopStage:
    name = "develop"

    def run(self, ctx: Context) -> None:
        arch: Architecture = ctx.get("architecture")
        res = model.call(arch.summary, purpose="develop-audit")
        ctx.meter(self.name, res, tags=[arch.artifact_id, "develop"])
        # Requirements traceability: every integration point covered in this reference run.
        ctx.put(
            "coverage",
            CoverageReport(
                items=[CoverageItem(requirement=r, state="covered") for r in arch.integration_map]
            ),
        )


class QAStage:
    """Owns the QA sign-off gate. Loops (via resume) until acceptance passes."""

    name = "qa"

    def run(self, ctx: Context) -> None:
        repo: Repo = ctx.get("repo")
        artifact_id = ctx.get("architecture").artifact_id
        handoff: QAHandoff = ctx.bag.get("qa") or QAHandoff(
            artifact_id=artifact_id,
            defects=[Defect("D1", "Edge case in input parsing")],
        )

        resp = ctx.responses.pop("qa-signoff", None)
        if resp is not None:
            for d in handoff.defects:
                d.resolved = True
            handoff.acceptance_passed = bool(resp.data.get("passed", True))

        res = model.call(repo.name, purpose="qa")
        ctx.meter(self.name, res, tags=[artifact_id, "qa"])
        ctx.put("qa", handoff)

        if not handoff.acceptance_passed:
            open_defects = [d for d in handoff.defects if not d.resolved]
            raise GatePause(
                "qa-signoff",
                "Tester sign-off required; open defects route back to Develop.",
                payload=[{"id": d.id, "description": d.description} for d in open_defects],
            )


class QACompleteStage:
    name = "qa-complete"

    def run(self, ctx: Context) -> None:
        handoff: QAHandoff = ctx.get("qa")
        res = model.call(handoff.artifact_id, purpose="qa-complete")
        ctx.meter(self.name, res, tags=[handoff.artifact_id, "qa-complete"])
        ctx.put(
            "change_request",
            ChangeRequest(
                artifact_id=handoff.artifact_id,
                summary=f"Release for {handoff.artifact_id}: {len(handoff.defects)} defect(s) resolved",
            ),
        )


class ChangeGateStage:
    """Owns the change-approval gate. Skipped cleanly when the profile disables it."""

    name = "change-gate"

    def run(self, ctx: Context) -> None:
        cr: ChangeRequest = ctx.get("change_request")

        if not ctx.profile.change_gate_enabled:
            cr.approved = True
            cr.approver = "auto (gate disabled by profile)"
            ctx.put("change_request", cr)
            return

        resp = ctx.responses.pop("change-approval", None)
        if resp is not None:
            cr.approved = bool(resp.data.get("approved", True))
            cr.approver = resp.data.get("approver", ctx.profile.approver)

        res = model.call(cr.summary, purpose="change-gate")
        ctx.meter(self.name, res, tags=[cr.artifact_id, "change-gate"])
        ctx.put("change_request", cr)

        if not cr.approved:
            raise GatePause(
                "change-approval",
                f"Change request awaiting approval from {ctx.profile.approver}.",
                payload={"artifact_id": cr.artifact_id, "summary": cr.summary},
            )


class PublishDocsStage:
    name = "publish-docs"

    def run(self, ctx: Context) -> None:
        arch: Architecture = ctx.get("architecture")
        targets = list(ctx.profile.docs_targets)
        published = [t for t in targets if t]
        res = model.call(arch.summary, purpose="publish-docs")
        ctx.meter(self.name, res, tags=[arch.artifact_id, "publish-docs"])
        ctx.put(
            "docs",
            DocSet(
                published_to=published,
                skipped=[t for t in targets if not t],
                fmt=ctx.profile.doc_format,
            ),
        )


DEFAULT_STAGES: list[Stage] = [
    IntakeStage(),
    ArchitectStage(),
    ScaffoldStage(),
    DevelopStage(),
    QAStage(),
    QACompleteStage(),
    ChangeGateStage(),
    PublishDocsStage(),
]


def _slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in text.strip()]
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:40] or "project"
