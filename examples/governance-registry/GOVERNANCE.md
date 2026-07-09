# Governance model (example)

This sanitized example shows how the registry organizes work so the pipeline can reason
over it. Everything here is generic.

## Artifact types

Every tracked thing is an artifact with a type. Representative vocabulary:

- `github-repo` -- a repository under governance
- `integration` -- a connector to an external system (object store, database, API)
- `audit` -- a point-in-time assessment (security, performance, configuration)
- `service` -- a long-running application or API
- `claude-skill` -- an agent skill
- `template` -- a reusable scaffold other repos are created from

## Tiers

A repo's `tier` custom property drives how strictly it is governed.

- `production` -- protected default branch, required review, no force-push (see
  `rulesets/production-tier.json`)
- `internal` -- standard hygiene expected, lighter protection
- `prototype` -- minimal gates, but secrets and license hygiene still apply

## Engagement profiles

A profile declares, for one engagement, how work arrives (intake channel), where it is
tracked, how change is approved, and where docs are published. Skills and the pipeline
read the active profile and adapt. Null fields are skipped, not errors. See
`profiles/` and the annotated `references/ENGAGEMENT-PROFILE-SCHEMA.yaml`.

## Standards

The onboarding interrogation scores a repo against `standards/checklist.yaml`. Each
standard has a severity; a committed secret is a blocker, license and CI are high, docs
and ignore hygiene are medium, agent-context files are low. The same list is encoded in
`pipeline/governance.py` so the code and the registry stay in agreement.

## How the pipeline uses this

- Intake matches an incoming request to a registry entry to produce tailored setup steps.
- Onboarding interrogates an existing repo against the standards and profile, then emits a
  conformance report and remediation plan.
- Change gate consults the profile's change-management config to decide whether to block a
  production deployment on approval.
