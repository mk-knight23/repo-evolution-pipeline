# Contributing

Thank you for improving Repo Evolution Pipeline.

## Development Workflow

1. Create a feature branch from main.
2. Keep changes focused and small.
3. Add or update tests for behavior changes.
4. Run local checks before opening a pull request.
5. Open a pull request using the project template.

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies from requirements.txt.
3. Configure .env from .env.example.

## Suggested Checks

```bash
pytest
python -m pipeline health
```

## Pull Request Guidelines

- Explain what changed and why.
- Link issues when applicable.
- Include a short test plan.
- Include screenshots or logs for API or dashboard changes.

## Code Style Expectations

- Prefer clear naming and explicit error handling.
- Keep functions focused and composable.
- Avoid unrelated refactors in feature pull requests.

## Documentation

Any change to orchestration behavior, API contracts, or configuration should update:

- README.md
- docs/README.md
- relevant docs in docs/architecture, docs/api, docs/configuration, or docs/operations
