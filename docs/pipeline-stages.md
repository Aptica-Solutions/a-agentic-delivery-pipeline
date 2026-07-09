# Pipeline stage contracts

Each stage is a single-purpose agent skill with an explicit contract. Stages hand
structured artifacts to one another, so the pipeline composes without any stage
needing to know the internals of the next. All vendor names are genericized:
"ITSM ticketing system", "work-tracking system", "docs platform".

---

## 1. Intake

**Purpose:** Turn an unstructured incoming request into a structured, registered
task with ready-to-run scaffolding steps.

**Triggers on:** a pasted email, ITSM ticket, chat message, or freeform description
of work, especially when it references a known system or artifact.

**Inputs:** the raw request; the governance registry entry for the referenced
artifact.

**Outputs:**
- A structured task entry in the task backlog.
- A discovery scaffold of work items in the work-tracking system (epic, features,
  discovery tasks).
- Tailored setup steps (clone, branch, environment) derived from the registry entry.

**Gate:** none.

**Notes:** when the work targets an existing repo, intake also accepts architecture
context from stage 2 and folds design decisions, integration map, and risk flags
into the task entry.

---

## 2. Architect

**Purpose:** Bridge requirements and build. Reason over requirements against the
engagement profile and produce the design artifacts that inform every downstream
stage.

**Inputs:** requirements in any format (email, work items, messages, documents,
freeform); the intake record.

**Outputs:**
- Solution design summary.
- Integration map.
- Risk and compliance flags.
- Work-item (epic/feature) refinement.
- A versioned `ARCHITECTURE.md` with a changelog.
- A scaffold seed for stage 3, with per-field confidence levels.

**Gate:** analyst Q&A loop. Open questions are formatted and routed to the business
analyst in the profile's preferred channel. The stage pauses, then resumes when
answers arrive, resolving questions, bumping the architecture version, and
regenerating outputs.

**Notes:** the scaffold seed is a byproduct, not the goal. The goal is a clean,
agreed architecture. Resume mode is detected from an existing `ARCHITECTURE.md`
plus incoming answers.

---

## 3. Scaffold / onboard

**Purpose:** Bring a repository under the enterprise template and governance standards
through a guided onboarding conversation rather than a form. Works two ways: scaffold a
brand-new repo, or onboard one that already exists.

**Inputs:** the scaffold seed from stage 2 (seeded mode), a fresh interactive run, or an
existing repository (or a set of them) to onboard.

**Outputs (new build):**
- A new private repo from the enterprise template.
- A filled onboarding document.
- A tailored environment starter.
- All setup commands needed to start coding.

**Outputs (existing repo / brownfield):**
- A completed onboarding survey capturing what the repo is and how it is run, the tribal
  knowledge inherited repos rarely have written down.
- A conformance report scoring the repo against the enterprise template and the governance
  registry: which standard assets are present or missing (CI, `ONBOARDING`, `ARCHITECTURE`,
  license, ignore hygiene, secret scanning), and where it drifts from the template.
- A remediation plan: the smallest ordered set of changes to reach conformance.

**Gate:** survey gate. Seeded mode only asks about fields the seed marked medium or low
confidence; high-confidence fields (including confirmed work-item IDs) are used directly.
For an existing repo, the gate is where a human confirms the interrogation's inferences
before any remediation is applied.

### Portfolio onboarding (brownfield)

Run the onboarding path across a portfolio to converge inherited, heterogeneous repos on
one standard incrementally. Each repo gets its own survey, conformance report, and
remediation plan; the registry accumulates a portfolio-wide view of what is and is not yet
conformant. This is the practical alternative to a big-bang standardization rewrite: one
human-checked conversation per repo, fanned across the fleet.

---

## 4. Develop audit

**Purpose:** Ad hoc requirements traceability during active development.

**Inputs:** the active branch; `ARCHITECTURE.md`; the work-item list. Accepts whatever
subset is present.

**Outputs:**
- A requirements-coverage report (covered / partial / gap).
- Work-item updates reflecting real state: in-progress, done, blocked, or gap found.

**Gate:** none.

**Notes:** deliberately toolchain-agnostic. It does not reach into the coding session;
it audits from the outside so it works regardless of which assistant or editor the
engineer uses. Typically run before opening a pull request.

---

## 5. QA loop

**Purpose:** Mirror the analyst Q&A loop downstream at the QA phase.

**Inputs:** tester feedback in any form (comment, email, message, defect list).

**Outputs:**
- Structured defect items.
- Work items kept current as issues resolve.
- On sign-off, a QA handoff context document for stage 6.

**Gate:** acceptance-criteria loop. Clarifications route back to the developer; the
loop ends only when the user confirms all acceptance criteria pass.

---

## 6. QA complete

**Purpose:** Bridge QA sign-off and the change gate.

**Inputs:** the QA handoff context from stage 5.

**Outputs:**
- A change-request package.
- Finalized work-item states reflecting QA completion.

**Gate:** none. Gathers no new information; if the handoff is missing one field, it
asks only for that field.

---

## 7. Change gate

**Purpose:** Enforce change management before a production deployment.

**Inputs:** the change-request package from stage 6 (or session context when run
standalone).

**Outputs:**
- The CR routed to the configured approver(s).
- Deployment steps blocked until approval is recorded.

**Gate:** change approval. Skipped cleanly when the profile declares no change gate.

---

## 8. Publish docs

**Purpose:** Format project artifacts to the engagement's deliverable spec and push
them to the configured documentation targets.

**Inputs:** architecture and onboarding artifacts; the profile's documentation config.

**Outputs:**
- Formatted deliverables published to the configured docs platform(s).
- A skip note logged for any target with null config, rather than an error.

**Gate:** none.

---

## Cross-cutting: telemetry

Any stage can emit a run record to [runmeter](https://github.com/Aptica-Solutions/a-mcp-runmeter)
tagged with the artifact id and stage name. Aggregating those records yields
cost-per-delivery, cost-per-stage, and error-rate views without adding a bespoke
logging table to each project.
