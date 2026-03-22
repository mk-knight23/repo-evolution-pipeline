# Production Deployment Guidance

## Current State

This repository does not ship production infrastructure manifests by default. It provides the application code, API server, and operational docs needed to deploy with your preferred platform.

## Recommended Runtime Topology

- API service process: handles run submission and diagnostics retrieval
- Worker process: executes pipeline workloads
- Shared persistent storage: run status, reports, checkpoints, clone cache
- Secret store: GitHub, GitLab, and LLM credentials

## Cloud Platform Options

- Container platforms: Cloud Run, ECS Fargate, Railway, Render
- VM based deployment: systemd managed service with reverse proxy
- Kubernetes: API Deployment plus worker Deployment and persistent volume

## Required External Services

- LLM provider credentials
- GitHub API token for source fetch fallback
- Optional GitLab token and target group for publish stage

## Production Checklist

1. Configure all required environment variables.
2. Isolate API and worker scaling profiles.
3. Store data artifacts on persistent storage.
4. Expose metrics endpoint and collect logs centrally.
5. Set run and API timeouts with retry policies.
6. Protect endpoints with authentication and network controls.
7. Rotate secrets regularly.

## Reliability Controls

- Use checkpoint resume and stage history.
- Keep push stage idempotency enabled.
- Keep diagnostics endpoint accessible for incident triage.
- Apply stage-level feature flags for emergency disable.
