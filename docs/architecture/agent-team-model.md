# Agent Team Model

This repository uses specialist agent teams with explicit handoffs.

## Team Roles

### Scanner Team

- Skill: source acquisition and filtering
- Input: manifest and source location
- Output: bounded source file map

### Analyzer Team

- Skill: intent extraction and product understanding
- Input: source files or metadata fallback
- Output: deep analysis or design brief

### Architect Team

- Skill: mobile system decomposition
- Input: analysis plus category heuristics
- Output: mobile architecture specification

### Generator Team

- Skill: file synthesis from architecture
- Input: architecture and context
- Output: generated mobile project files

### Verification Team

- Skill: executable quality checks
- Input: generated files
- Output: verification report with check-level diagnostics

### Repair Team

- Skill: targeted fix planning
- Input: verification failure category and relevant files
- Output: patch plan applied to generated files

### Quality Team

- Skill: governance and release readiness
- Input: generated files and architecture
- Output: quality gates and score

### Push Team

- Skill: repository publication and idempotency
- Input: approved generated output
- Output: GitLab project URL and audit entries

## Team Handoff Contract

Each handoff carries:

- current state snapshot
- stage outcome status
- warnings and errors
- retry eligibility
- telemetry context

This keeps stage behavior deterministic and debuggable across batch runs.
