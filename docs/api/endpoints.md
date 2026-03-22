# API Endpoints

Base service is defined in pipeline.api.server.

## GET /

Returns basic service metadata.

## GET /health

Runs dependency and environment health checks.

## GET /version

Returns service and pipeline version info.

## GET /metrics

Returns Prometheus-compatible metrics payload.

## GET /status

Returns current or latest run status from data artifacts.

## POST /run

Starts batch processing in background.

Request fields:

- manifests: array of RepoManifest payloads
- batch_size: optional
- max_concurrent: optional
- enabled_stages: optional list of stage names

## POST /run-single

Starts single-repository background processing.

Request fields:

- repo: owner and repository name
- category: repository category
- enabled_stages: optional list of stage names

## GET /report/{run_id}

Returns final run report file when present.

## GET /diagnostics/{run_id}

Returns merged diagnostics payload:

- final report if available
- live status if current run matches
- run-filtered event history
