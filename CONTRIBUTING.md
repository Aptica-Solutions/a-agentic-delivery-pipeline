# Contributing

Thanks for your interest. This repository is the **genericized reference design** for an
AI-native, skills-driven delivery pipeline. It documents the pattern, the stage contracts,
and (as it grows) a small runnable reference implementation. The production skill
implementations, engagement profiles, and registry that inspired it are internal and are
not part of this repo.

## What belongs here

- The flow and stage contracts ([README.md](README.md), [docs/pipeline-stages.md](docs/pipeline-stages.md))
- Diagram source and exports ([docs/pipeline.mmd](docs/pipeline.mmd) and rendered variants)
- A minimal, dependency-light reference implementation that demonstrates the pattern
- Examples that are useful independent of any one vendor or client

## What does not belong here

- Client names, engagement details, or anything tied to a specific customer
- Real credentials, tokens, endpoints, or private URLs
- Vendor-specific coupling presented as required. Keep tool categories abstract
  ("ITSM ticketing system", "work-tracking system", "docs platform") so the pattern
  reads independently of any stack.

## Ground rules

- **Keep it genericized.** If a change would reveal client or engagement specifics, stop
  and abstract it first.
- **Low total cost of ownership.** Prefer the standard library and a tiny dependency
  surface. New dependencies need a clear justification.
- **Match the contracts.** A stage change should keep the documented input/output contract
  in `docs/pipeline-stages.md` accurate. Update the doc in the same change.
- **Small, reviewable changes.** One concern per pull request.

## Working the diagram

The canonical diagram source is [docs/pipeline.mmd](docs/pipeline.mmd) (Mermaid, renders
natively on GitHub). The PNG and SVG exports are generated from the same design. If you
change the flow, update the Mermaid source and regenerate the exports so all variants stay
in sync.

## Development

If you are adding to the reference implementation:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Keep new code typed, keep functions small, and add a test alongside any behavior change.

## Pull requests

1. Fork and branch from `main`.
2. Make the change; update docs and diagram exports if the flow moved.
3. Run the tests.
4. Open a PR describing what changed and why, in plain language.

## License

By contributing you agree that your contributions are licensed under the repository's
[MIT License](LICENSE).
