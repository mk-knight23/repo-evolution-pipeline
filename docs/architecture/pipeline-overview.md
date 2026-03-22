# Pipeline Overview

Repo Evolution Pipeline is a staged orchestration system that converts source repositories into mobile outputs.

## Runtime Flow

1. Scanner acquires source files through clone or API fallback.
2. Analyzer generates deep analysis or metadata fallback design brief.
3. Architect selects framework, navigation, dependencies, and screens.
4. CodeGen creates full project files in memory.
5. Verifier executes install and quality commands on materialized output.
6. Repair loop applies targeted edits when verification fails.
7. Quality gates compute scoring and governance checks.
8. Pusher publishes to GitLab when policy permits.

## State Contract

The central unit is RepoEvolutionState.

Key fields include:

- manifest
- source_files
- deep_analysis or design_brief
- architecture
- generated_files
- verification_report
- generation_result
- warnings and errors
- stage_history and checkpoint schema version

## Durability And Observability

- Checkpoint files are atomic and versioned.
- Stage execution history records started, completed, and failed attempts.
- Event bus stores run-aware history with run ID and correlation ID.
- Diagnostics endpoint aggregates report, status, and event timeline.
