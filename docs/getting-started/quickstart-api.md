# Quickstart API

## Start Server

```bash
python -m pipeline api --host 0.0.0.0 --port 8000 --reload
```

## Verify Service

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

## Start Batch Run

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "manifests": [
      {
        "name": "demo",
        "github_url": "https://github.com/owner/demo",
        "description": "demo",
        "category": "webapp"
      }
    ],
    "batch_size": 2,
    "max_concurrent": 2
  }'
```

## Start Single Run

```bash
curl -X POST http://localhost:8000/run-single \
  -H "Content-Type: application/json" \
  -d '{"repo":"owner/demo","category":"webapp"}'
```

## Pull Reports And Diagnostics

```bash
curl http://localhost:8000/status
curl http://localhost:8000/report/run-xxxx
curl http://localhost:8000/diagnostics/run-xxxx
```
