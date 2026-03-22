"""
FastAPI Server — wraps the Repo Evolution Pipeline as a service.
Provides endpoints for triggered runs, status monitoring, and health checks.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from pipeline.core.orchestrator import PipelineOrchestrator
from pipeline.core.models import (
    RepoManifest, 
    RepoCategory
)
from pipeline.core.config import config
from pipeline.core.event_bus import event_bus
from pipeline.monitoring.dashboard import run_health_check
from pipeline.core.telemetry import metrics
from pipeline.core.logging import generate_correlation_id

# Initialize FastAPI
app = FastAPI(
    title="Repo Evolution Pipeline API",
    description="Automated GitHub to GitLab Mobile App Converter",
    version=config.pipeline_version,
)


# ── Correlation ID Middleware ──────────────────────────────────────────────

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Inject X-Correlation-ID header for request tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", generate_correlation_id())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


logger = logging.getLogger("pipeline.api")


# ── Request Models ─────────────────────────────────────────────────────────

class BatchRunRequest(BaseModel):
    manifests: List[RepoManifest]
    batch_size: Optional[int] = 5
    max_concurrent: Optional[int] = 3
    enabled_stages: Optional[List[str]] = None


class SingleRunRequest(BaseModel):
    repo: str  # Format: "user/repo-name"
    category: str = "webapp"
    enabled_stages: Optional[List[str]] = None


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "Repo Evolution Pipeline",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Run dependency and environment health checks."""
    return run_health_check()


@app.get("/version")
async def version():
    """Return pipeline version information."""
    return {
        "version": config.pipeline_version,
        "service": "Repo Evolution Pipeline",
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """Export Prometheus-compatible metrics."""
    return metrics.export_prometheus()


@app.get("/status")
async def get_overall_status():
    """Retrieve the current progress of the last/current run."""
    status_path = Path("data/evolution-status.json")
    if not status_path.exists():
        return {"status": "idle", "message": "No runs found in data directory"}
    
    try:
        return json.loads(status_path.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading status: {e}")


@app.post("/run")
async def run_batch(request: BatchRunRequest, background_tasks: BackgroundTasks):
    """Start a batch processing run in the background."""
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    orchestrator = PipelineOrchestrator()
    # Start the orchestrator in the background with per-run overrides.
    background_tasks.add_task(
        orchestrator.run_all,
        request.manifests,
        request.batch_size,
        request.max_concurrent,
        request.enabled_stages,
        run_id,
    )
    
    return {
        "message": f"Batch run started for {len(request.manifests)} repositories",
        "run_id": run_id,
        "batch_size": request.batch_size or config.batch_size,
        "max_concurrent": request.max_concurrent or config.max_concurrent,
    }


@app.post("/run-single")
async def run_single(request: SingleRunRequest, background_tasks: BackgroundTasks):
    """Start processing a single repository in the background."""
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    # Map category string to enum
    cat_map = {c.value: c for c in RepoCategory}
    repo_category = cat_map.get(request.category, RepoCategory.WEBAPP)

    manifest = RepoManifest(
        name=request.repo.split("/")[-1],
        github_url=f"https://github.com/{request.repo}",
        description=f"Mobile conversion of {request.repo}",
        category=repo_category,
    )

    orchestrator = PipelineOrchestrator()
    # background run_single
    background_tasks.add_task(orchestrator.run_single, manifest, request.enabled_stages, run_id)

    return {
        "message": f"Single run started for {request.repo}",
        "run_id": run_id,
        "manifest": manifest.model_dump()
    }


@app.get("/report/{run_id}")
async def get_report(run_id: str):
    """Retrieve the final report for a specific run ID."""
    report_path = Path("data") / f"report-{run_id}.json"
    if not report_path.exists():
        # Try finding it without 'run-' prefix if needed
        if not run_id.startswith("run-"):
            report_path = Path("data") / f"report-run-{run_id}.json"
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail=f"Report for run {run_id} not found")

    try:
        return json.loads(report_path.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading report: {e}")


@app.get("/diagnostics/{run_id}")
async def get_run_diagnostics(run_id: str, limit: int = 100):
    """Retrieve consolidated diagnostics for a run, including report, live status, and event history."""
    report_path = Path("data") / f"report-{run_id}.json"
    if not report_path.exists() and not run_id.startswith("run-"):
        alt = Path("data") / f"report-run-{run_id}.json"
        if alt.exists():
            report_path = alt

    report = None
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading report: {e}")

    status = None
    status_path = Path("data/evolution-status.json")
    if status_path.exists():
        try:
            current_status = json.loads(status_path.read_text())
            if current_status.get("run_id") == run_id:
                status = current_status
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading status: {e}")

    events = [
        {
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "run_id": event.run_id,
            "correlation_id": event.correlation_id,
            "repo": event.repo,
            "stage": event.stage,
            "payload": event.payload,
        }
        for event in event_bus.get_history(run_id=run_id, limit=limit)
    ]

    if report is None and status is None and not events:
        raise HTTPException(status_code=404, detail=f"Diagnostics for run {run_id} not found")

    return {
        "run_id": run_id,
        "report": report,
        "status": status,
        "events": events,
        "event_count": len(events),
    }
