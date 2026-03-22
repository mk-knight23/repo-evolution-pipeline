# Operations Runbook

## Standard Run Lifecycle

1. Submit run through CLI or API.
2. Monitor status and event flow.
3. Review final report and quality score.
4. Investigate diagnostics for failed runs.
5. Re-run with scoped stages if needed.

## Operational Commands

```bash
python -m pipeline health
python -m pipeline run-single --repo owner/repo --category webapp
```

API checks:

```bash
curl http://localhost:8000/status
curl http://localhost:8000/metrics
curl http://localhost:8000/diagnostics/<run_id>
```

## Incident Triage

1. Confirm health endpoint status.
2. Fetch diagnostics for impacted run.
3. Identify failed stage and failure category.
4. Inspect checkpoint and stage history for resume strategy.
5. Re-run with targeted stages if recovery is safe.

## Recovery Patterns

- Scanner failures: verify token scopes and source reachability.
- Verification failures: inspect relevant files and rerun repair-enabled flow.
- Push failures: verify GitLab credentials and group permissions.
- Metrics or status drift: verify filesystem write permissions in data directory.
