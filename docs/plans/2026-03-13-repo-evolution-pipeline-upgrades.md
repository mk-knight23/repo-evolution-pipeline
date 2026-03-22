# Repo Evolution Pipeline Upgrades Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the CLI pipeline more correct, more verifiable, and easier to extend (stages/plugins), while improving generated output quality and aligning docs/tests with implemented behavior.

**Architecture:** Keep the current `pipeline/` CLI orchestrator, but introduce (1) a stage registry (“plugins”) so stages can be enabled/disabled and extended cleanly, and (2) a verification loop (lint/typecheck/tests/build) that can run locally in a sandbox and feed results back into generation/repair.

**Tech Stack:** Python 3.11+, Pydantic v2, LangChain (Anthropic + DashScope via OpenAI-compatible endpoint), python-gitlab, PyGithub/requests.

---

## Why these upgrades (web research patterns)

- **Agentic coding platforms** emphasize a tight “generate → run checks → repair” loop to reach working code, not just plausible code (e.g., SWE-bench-style harnesses; OpenHands/OpenDevin test-and-fix loops). citeturn2search3turn2search2turn2search1
- **Repo context compression** (“repo map” / dependency graph / relevance slicing) is a core technique to keep prompts small while staying accurate; your `ProjectContextManager` is a good start but needs tighter integration into analysis/codegen. citeturn1search3
- **GitLab automation** should respect API limits and prefer fewer, larger commits with clear provenance + CI artifacts; python-gitlab supports this workflow well but needs careful error handling and idempotency. citeturn0search3

---

## Phase 0 (this session): Correctness + quality score quick wins

### Task 0.1: Make generation produce CI + architecture docs (so gates match reality)

**Files:**
- Modify: `pipeline/agents/codegen.py`
- Modify: `pipeline/quality/gates.py`
- Test: `pipeline/tests/test_quality.py`

**Step 1: Write/adjust failing test**
- Update fixtures/expectations so generated files include `.gitlab-ci.yml` and `ARCHITECTURE.md`.

**Step 2: Run test to verify it fails**
- Run: `pytest pipeline/tests/test_quality.py -q`
- Expected: CI/docs gates fail or warn because generator doesn’t create them.

**Step 3: Implement minimal code**
- In `generate_mobile_code()`, add:
  - `.gitlab-ci.yml` using `pipeline/agents/ci_templates.py`
  - `ARCHITECTURE.md` describing screens, nav, state, key deps

**Step 4: Run test to verify it passes**
- Run: `pytest pipeline/tests/test_quality.py -q`
- Expected: PASS

---

### Task 0.2: Remove “TODO:” placeholders from generated shipping code

**Files:**
- Modify: `pipeline/agents/codegen.py`
- Test: `pipeline/tests/test_quality.py`

**Step 1: Add test**
- Add a test asserting the `no_placeholder_content` gate stays `PASSED` for generator output.

**Step 2: Implement**
- Replace `TODO:` comments in generated TS/TSX (not docs) with non-placeholder phrasing.

---

### Task 0.3: Fix `pipeline quality` CLI output (it prints empty `gate.message`)

**Files:**
- Modify: `pipeline/__main__.py`
- Modify: `pipeline/quality/gates.py`
- Test: `pipeline/tests/test_quality.py` (optional)

**Implementation**
- Ensure each `QualityGate` sets a user-facing `message` (short) and `details` (long).
- Print `gate.message` (or `gate.details` fallback) in the CLI.

---

### Task 0.4: Make `reconstruct_project.py` write real PNG files

**Files:**
- Modify: `reconstruct_project.py`

**Implementation**
- When writing `*.png` from `state.generated_files`, base64-decode before writing bytes.

---

## Phase 1: “Verify + Repair” loop (production-grade)

### Task 1.1: Add a verifier module

**Files:**
- Create: `pipeline/quality/verifier.py`
- Modify: `pipeline/core/orchestrator.py`
- Test: `pipeline/tests/test_verifier.py`

**Behavior**
- Given a generated project (file map), run:
  - `npm ci`
  - `npm run lint`
  - `npm run type-check`
  - `npm test`
  - (optional) `expo export --platform web`
- Capture stdout/stderr and produce structured results.

### Task 1.2: Add an auto-repair step

**Files:**
- Create: `pipeline/agents/repair.py`
- Modify: `pipeline/agents/codegen.py`
- Modify: `pipeline/core/orchestrator.py`

**Behavior**
- If verifier fails, call LLM with (diff + errors + key files) and produce a patch to apply to `generated_files`.
- Re-verify up to `N` attempts.

---

## Phase 2: Extensibility (“plugins” / stage registry)

### Task 2.1: Stage registry

**Files:**
- Create: `pipeline/core/stages.py`
- Modify: `pipeline/core/orchestrator.py`

**Behavior**
- Define an interface (callable) per stage.
- Allow enabling/disabling stages via config/env.

---

## Phase 3: MCP / external integrations (optional)

If you want this to run as a service, add:
- an MCP server that exposes `scan_repo`, `generate_mobile_app`, `push_gitlab`, `get_report`, and `rerun_with_repair`.
- or a FastAPI server (as described in `CLAUDE.md`) that wraps the same orchestration.

