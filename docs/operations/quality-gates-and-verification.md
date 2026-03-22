# Quality Gates And Verification

## Verification

Verification executes generated output in a temporary project workspace and runs concrete checks.

Typical check sequence:

- Dependency install
- Lint
- Type check
- Test
- Optional web export

Verification report includes per-check command, status, duration, and logs.

## Failure Taxonomy

Failure categories include:

- dependencies
- lint
- types
- tests
- build
- timeout
- infrastructure
- verification

This taxonomy feeds the repair prompt and diagnostics endpoint.

## Repair Loop

When enabled, repair uses failure category and relevant file hints to request narrow edits, then re-runs verification.

## Quality Gates

Quality gates evaluate generated output for:

- baseline project structure
- required files and docs
- security and secret leak checks
- maintainability and reliability indicators
- consistency and readiness checks

Final quality score is recorded in generation_result and run report.
