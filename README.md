# Repo Evolution Pipeline

AI-powered multi-agent system that transforms GitHub repositories into mobile-ready implementations with verification, quality gates, diagnostics, and optional GitLab publishing.

## What This Repository Does

Repo Evolution Pipeline automates the path from source repository discovery to validated mobile output.

- Ingests repository manifests or single repositories.
- Scans source code through git clone or GitHub API fallback.
- Produces analysis and a mobile architecture plan.
- Generates mobile project files for Expo or React Native.
- Runs real verification commands on generated output.
- Applies targeted repair loops when verification fails.
- Computes quality and security gate results.
- Optionally pushes generated output to GitLab with idempotent safeguards.

## Why This Exists

Converting many repositories into mobile-ready implementations is repetitive, error-prone, and hard to standardize. This project provides a durable, observable pipeline with explicit stage ownership and handoffs so teams can scale conversion quality and throughput.

## How The Pipeline Works

### Stage Flow

Scanner -> Analyzer -> Architect -> CodeGen -> Verifier -> Quality Gates -> Pusher

### End-to-End Runtime

1. Input manifests are accepted by CLI or API.
2. Each repository enters a stateful run context.
3. Stages execute in sequence with checkpointing and event emission.
4. Verification failures can trigger targeted repair and re-verification.
5. Final reports and diagnostics are persisted in data artifacts.

## Agent Teams And Skills

The project follows a team-of-agents operating model where each stage is a specialist team with explicit contracts.

| Team | Primary Skill | Inputs | Outputs |
| --- | --- | --- | --- |
| Scanner Team | Source acquisition and filtering | Repo manifest, URL, optional commit SHA | Source file map |
| Analyzer Team | Product and code intent analysis | Source files or metadata fallback | Deep analysis or design brief |
| Architect Team | Mobile system design | Analysis brief, category heuristics | Mobile architecture |
| Generator Team | Project synthesis | Architecture, analysis context | Generated files |
| Verification Team | Build and quality execution | Generated files | Verification report |
| Repair Team | Minimal fix planning | Verification diagnostics | Patched generated files |
| Quality Team | Governance and scoring | Generated files, architecture | Quality gate results and score |
| Push Team | Repository publication | Generated output and metadata | GitLab repository URL and audit record |

## Architecture At A Glance

- Orchestrator: pipeline.core.orchestrator.PipelineOrchestrator
- State model: pipeline.core.models.RepoEvolutionState
- Stage registry: pipeline.core.stages
- API service: pipeline.api.server
- Monitoring: pipeline.monitoring.dashboard
- Verification and gates: pipeline.quality.verifier and pipeline.quality.gates

## Repository Layout

```text
pipeline/
  agents/          Scanner, analyzer, architect, codegen, repair, pusher
  core/            Config, models, orchestrator, event bus, telemetry
  quality/         Verifier and quality gates
  monitoring/      Dashboard and status tracking
  api/             FastAPI server

docs/
  architecture/    Pipeline and team model docs
  getting-started/ Local setup and quickstarts
  deployment/      Local and production deployment guidance
  operations/      Runbooks and quality/verification operations
  configuration/   Environment variable contract
  api/             Endpoint reference
```

## Quickstart

### Prerequisites

- Python 3.10+
- Node.js 18+ (required for generated project verification)
- GitHub token for source fetches
- Optional GitLab token for push stage

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
# Fill required tokens and org/group values
```

## CLI Usage

Run batch from manifests:

```bash
python -m pipeline run --manifests data/manifests.example.json --batch-size 5 --max-concurrent 3
```

Run single repository:

```bash
python -m pipeline run-single --repo owner/repo-name --category webapp
```

Health checks:

```bash
python -m pipeline health
```

Quality checks on generated files:

```bash
python -m pipeline quality --files-dir ./output
```

Start API server:

```bash
python -m pipeline api --host 0.0.0.0 --port 8000 --reload
```

## API Usage

Core endpoints:

- GET /
- GET /health
- GET /version
- GET /metrics
- GET /status
- POST /run
- POST /run-single
- GET /report/{run_id}
- GET /diagnostics/{run_id}

Example batch run:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "manifests": [
      {
        "name": "example-repo",
        "github_url": "https://github.com/owner/example-repo",
        "description": "Sample",
        "category": "webapp"
      }
    ],
    "batch_size": 3,
    "max_concurrent": 2
  }'
```

## Quality, Verification, And Repair

- Verification executes real install, lint, type-check, test, and optional web export commands.
- Failures are categorized (dependencies, lint, types, tests, build, timeout, infrastructure, verification).
- Repair loop receives failure summary and relevant file hints for targeted edits.
- Quality gates score generated output across structure, security, reliability, and maintainability checks.

## Data Artifacts

- data/checkpoint-<repo>.json
- data/report-<run_id>.json
- data/evolution-status.json
- data/clone-cache/<cache_key>.json
- data/logs/push_audit.jsonl (generated when push runs)

## Environment Variables

See docs/configuration/environment-variables.md for the full contract and examples.

## Deployment

- Local development: docs/deployment/local-dev.md
- Production guidance: docs/deployment/production.md

## Publish To GitHub

If this workspace is not yet connected to GitHub, use the following one-time setup:

```bash
git init
git add .
git commit -m "chore: initialize repo evolution pipeline"
git branch -M main
git remote add origin https://github.com/<your-org-or-user>/repo-evolution-pipeline.git
git push -u origin main
```

After that, collaboration features in this repository are ready:

- Issue templates in .github/ISSUE_TEMPLATE
- Pull request template in .github/pull_request_template.md
- Docs link checker in .github/workflows/docs-link-check.yml

## Observability

- Run events with run ID and correlation ID.
- Consolidated run diagnostics endpoint.
- Prometheus-compatible metrics endpoint.

## Documentation Map

- Docs index: docs/README.md
- Pipeline architecture: docs/architecture/pipeline-overview.md
- Agent team model: docs/architecture/agent-team-model.md
- Local setup: docs/getting-started/local-setup.md
- CLI quickstart: docs/getting-started/quickstart-cli.md
- API quickstart: docs/getting-started/quickstart-api.md
- Operations runbook: docs/operations/runbook.md
- API reference: docs/api/endpoints.md
- FAQ: docs/faq.md

## Current Limits

- GitHub repository creation is not automated in this codebase.
- GitLab push is optional and depends on configured credentials.
- Queue backends and external state stores are documented but not required for local operation.

## Contributing

See CONTRIBUTING.md.

## Security

See SECURITY.md.

## Support

See SUPPORT.md.

## License

MIT License. See LICENSE.
