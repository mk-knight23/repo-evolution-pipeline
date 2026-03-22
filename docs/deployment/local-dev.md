# Local Development Deployment

## Purpose

This mode runs all services on a single developer machine.

## Process Model

- Pipeline CLI for direct runs
- FastAPI process for service-driven runs
- Local filesystem for status, checkpoints, and reports

## Commands

```bash
python -m pipeline api --host 0.0.0.0 --port 8000
```

In a separate shell:

```bash
python -m pipeline run --manifests data/manifests.example.json
```

## Data Paths

- data/evolution-status.json
- data/report-<run_id>.json
- data/checkpoint-<repo>.json
- data/clone-cache/
- data/logs/push_audit.jsonl when push stage runs

## Local Hardening Checklist

- Keep .env out of version control.
- Use low privilege personal tokens.
- Enable only required pipeline stages when debugging.
- Validate generated output before enabling push stage.
