# Agentic Pipeline Upgrade Plan (2026-03-22)

## 1. Research Summary (How production-grade projects like this work)

This plan is based on patterns from:
- LangGraph docs (durable execution, stateful workflows, human-in-the-loop, observability)
- Anthropic SWE-bench engineering writeup (simple scaffold, strong tool interfaces, generate-run-fix loops)
- GitLab CI docs (pipeline decomposition, dependency-aware jobs, secure variable handling)

Common architecture patterns across successful agentic software pipelines:
1. Deterministic state machine with durable checkpoints.
2. Tight generate -> verify -> repair loop with bounded retries.
3. Strong execution contracts for each stage (inputs, outputs, diagnostics, timings).
4. Idempotent side effects (especially clone/push/publish).
5. Deep observability: run timeline, stage attempts, failure classes, and cost metrics.
6. Security defaults: secret redaction, safe variable handling, strict gateing before publish.
7. Evaluation harness to prevent regressions in quality and reliability.

## 2. What this repository already has

Implemented now:
- Stage-oriented orchestrator with registry and ordered execution.
- Checkpointing and resume support per repository.
- Verification engine that runs install/lint/type-check/test.
- Optional repair loop after failed verification.
- Quality gates with weighted score and security scans.
- Event bus and metrics endpoint.
- GitLab push automation and audit log writing.

Strengths:
- Clear stage boundaries.
- Good initial reliability controls (retries, circuit breaker, checkpoints).
- Good quality discipline (verification + gates + docs generation).

## 3. Current structural gaps

1. API run isolation (global config mutation under concurrent API runs).
2. Resume logic uses heuristics in places instead of explicit stage journal.
3. Side-effect stages need explicit idempotency keys and duplicate protection.
4. Verification diagnostics are not normalized enough for targeted repair policies.
5. No formal plugin contract/discovery for external stage extensions.
6. No regression harness that replays fixed manifests and checks outcome stability.
7. Version metadata drift across API/config/project metadata.

## 4. Upgrade roadmap

### Phase 0 (Quick Wins)
- Remove API-level global config mutation and move to per-run overrides.
- Add stage execution metadata (attempt, duration, result) to state.
- Unify version source of truth.

### Phase 1 (Reliability)
- Add explicit per-stage execution journal to checkpoints.
- Atomic checkpoint writes with schema versioning.
- Add idempotency key strategy for clone/push side effects.

### Phase 2 (Verify/Repair)
- Add verification failure taxonomy (dependency, lint, typing, test, build, infra).
- Add per-failure retry budget and repair policies.
- Repair only relevant files based on diagnostics + confidence threshold.

### Phase 3 (Extensibility + Observability)
- Stage plugin API and registration boundaries.
- Run diagnostics endpoint with event timeline.
- Enhanced telemetry for top failure reasons and p95 by stage.

### Phase 4 (Evaluation + Security)
- Replay harness for regression checks (quality score + verification outcome).
- Secret redaction enforcement in logs/events.
- Security gate hard block before push on critical findings.

## 5. Work started in this session

Implemented:
- API endpoints now use per-request orchestrator instances.
- API no longer mutates global config for batch/single runs.
- Orchestrator now accepts per-run overrides:
  - batch_size
  - max_concurrent
  - enabled_stages
  - run_id
- Added explicit stage execution journal to state (`stage_history`).
- Orchestrator now records stage started/completed/failed entries with attempt and duration.
- Resume now prefers journal-based skipping of already completed stages (legacy heuristics retained as fallback).
- Added commit-aware clone cache idempotency in scanner when `commit_sha` is available.
- Added audit-log based push idempotency lookup keyed on manifest/architecture/generated file content.
- Added structured verifier failure diagnostics: category, summary, first failed check, relevant file hints.
- Repair agent now uses verifier diagnostics to target prompt context and prioritize relevant files.
- Added run-aware event metadata (`run_id`, `correlation_id`) and filtering in event history.
- Added diagnostics API endpoint for consolidated run report/status/events retrieval.
- Fixed monitor updates for checkpoint-resumed and successfully completed/skipped repos.
- Added tests validating override isolation and no global mutation.
- Added tests for stage journal + checkpoint roundtrip.
- Added tests for clone cache and push deduplication behavior.
- Added tests for failure taxonomy and targeted repair prompting.
- Added tests for diagnostics endpoint and single-run run_id propagation.

Changed files:
- pipeline/core/orchestrator.py
- pipeline/api/server.py
- pipeline/core/models.py
- pipeline/agents/scanner.py
- pipeline/agents/pusher.py
- pipeline/quality/verifier.py
- pipeline/agents/repair.py
- pipeline/core/event_bus.py
- pipeline/tests/test_api_run_overrides.py
- pipeline/tests/test_models.py
- pipeline/tests/test_scanner.py
- pipeline/tests/test_pusher.py
- pipeline/tests/test_verifier.py
- pipeline/tests/test_repair.py
- pipeline/api/server.py

Validation:
- Targeted tests passed for API override isolation, stage journal reliability, clone cache idempotency, push deduplication, verifier failure taxonomy, targeted repair prompting, and diagnostics endpoint changes.

## 6. Next implementation step (recommended)

Implement explicit stage execution journal in RepoEvolutionState and resume from journal instead of inferred state fields.

Rationale:
- Highest reliability gain per effort after API isolation.
- Enables deterministic replay and better observability.
