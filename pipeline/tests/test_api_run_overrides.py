import asyncio
import json

from fastapi import BackgroundTasks

from pipeline.api import server
from pipeline.core.config import config
from pipeline.core.event_bus import event_bus, PipelineEvent
from pipeline.core.models import RepoCategory, RepoManifest


class DummyOrchestrator:
    run_all_calls: list[dict] = []
    run_single_calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def run_all(
        self,
        manifests,
        batch_size=None,
        max_concurrent=None,
        enabled_stages=None,
        run_id="",
    ):
        self.__class__.run_all_calls.append(
            {
                "manifests": manifests,
                "batch_size": batch_size,
                "max_concurrent": max_concurrent,
                "enabled_stages": enabled_stages,
                "run_id": run_id,
            }
        )

    async def run_single(self, manifest, enabled_stages=None, run_id=""):
        self.__class__.run_single_calls.append(
            {
                "manifest": manifest,
                "enabled_stages": enabled_stages,
                "run_id": run_id,
            }
        )


def test_run_batch_uses_overrides_without_mutating_global_config(monkeypatch):
    monkeypatch.setattr(server, "PipelineOrchestrator", DummyOrchestrator)
    DummyOrchestrator.run_all_calls.clear()

    orig_batch = config.batch_size
    orig_max_concurrent = config.max_concurrent
    orig_enabled_stages = list(config.enabled_stages)

    request = server.BatchRunRequest(
        manifests=[
            RepoManifest(
                name="demo",
                github_url="https://github.com/user/demo",
                category=RepoCategory.WEBAPP,
            )
        ],
        batch_size=2,
        max_concurrent=1,
        enabled_stages=["cloning", "analyzing"],
    )

    background = BackgroundTasks()
    response = asyncio.run(server.run_batch(request, background))

    assert config.batch_size == orig_batch
    assert config.max_concurrent == orig_max_concurrent
    assert list(config.enabled_stages) == orig_enabled_stages
    assert response["batch_size"] == 2
    assert response["max_concurrent"] == 1
    assert response["run_id"].startswith("run-")

    asyncio.run(background())

    assert len(DummyOrchestrator.run_all_calls) == 1
    call = DummyOrchestrator.run_all_calls[0]
    assert call["batch_size"] == 2
    assert call["max_concurrent"] == 1
    assert call["enabled_stages"] == ["cloning", "analyzing"]
    assert call["run_id"] == response["run_id"]


def test_run_single_uses_enabled_stage_override_without_global_mutation(monkeypatch):
    monkeypatch.setattr(server, "PipelineOrchestrator", DummyOrchestrator)
    DummyOrchestrator.run_single_calls.clear()

    orig_enabled_stages = list(config.enabled_stages)

    request = server.SingleRunRequest(
        repo="user/my-app",
        category="webapp",
        enabled_stages=["cloning", "analyzing", "architecting"],
    )

    background = BackgroundTasks()
    response = asyncio.run(server.run_single(request, background))

    assert list(config.enabled_stages) == orig_enabled_stages
    assert response["manifest"]["name"] == "my-app"

    asyncio.run(background())

    assert len(DummyOrchestrator.run_single_calls) == 1
    call = DummyOrchestrator.run_single_calls[0]
    assert call["enabled_stages"] == ["cloning", "analyzing", "architecting"]
    assert call["manifest"].name == "my-app"
    assert call["run_id"].startswith("run-")


def test_get_run_diagnostics_returns_report_status_and_events(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    event_bus.clear()

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    run_id = "run-abc123"

    (data_dir / f"report-{run_id}.json").write_text(
        json.dumps({"run_id": run_id, "completed": 1}),
        encoding="utf-8",
    )
    (data_dir / "evolution-status.json").write_text(
        json.dumps({"run_id": run_id, "completed": 0, "in_progress": 1}),
        encoding="utf-8",
    )

    asyncio.run(
        event_bus.emit(
            PipelineEvent.STAGE_STARTED,
            {
                "run_id": run_id,
                "repo": "demo",
                "stage": "cloning",
                "correlation_id": "cid123",
            },
        )
    )

    diagnostics = asyncio.run(server.get_run_diagnostics(run_id, limit=10))

    assert diagnostics["run_id"] == run_id
    assert diagnostics["report"]["run_id"] == run_id
    assert diagnostics["status"]["run_id"] == run_id
    assert diagnostics["event_count"] == 1
    assert diagnostics["events"][0]["run_id"] == run_id
    assert diagnostics["events"][0]["repo"] == "demo"


def test_get_run_diagnostics_raises_for_unknown_run(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    event_bus.clear()

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        asyncio.run(server.get_run_diagnostics("run-missing", limit=10))

    assert exc.value.status_code == 404
