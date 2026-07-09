# Example governance registry (sanitized)

A small, sanitized example of the governance registry the pipeline reads. It mirrors the
shape of a real registry, engagement profiles, per-artifact entries, schemas, a branch
ruleset, and the standards checklist, with entirely generic content. No client names, no
real systems, no credentials.

The brownfield onboarding path scores existing repos against the standards in
[`standards/checklist.yaml`](standards/checklist.yaml); the same standards are encoded in
`pipeline/governance.py`. Engagement profiles ([`profiles/`](profiles)) drive which tools
and gates apply. Registry entries ([`registry/`](registry)) are the source of truth for
what each artifact is and how to scaffold or onboard it.

```
governance-registry/
├── profiles/                 engagement profiles (config over code)
│   ├── example-internal.yaml
│   └── example-client.yaml
├── registry/                 one entry per tracked artifact
│   ├── example-repo-template.yaml
│   ├── example-integration-object-store.yaml
│   └── example-audit-database-security.yaml
├── references/               annotated schemas (reference only)
│   ├── ENGAGEMENT-PROFILE-SCHEMA.yaml
│   └── REGISTRY-ENTRY.template.yaml
├── rulesets/
│   └── production-tier.json  branch protection for production-tier repos
├── standards/
│   └── checklist.yaml        what the governance interrogation checks
└── GOVERNANCE.md             types, tiers, and how the pieces fit
```

This directory is illustrative. In a real deployment the registry is its own repository so
it can be versioned, reviewed, and referenced independently of any one project.
