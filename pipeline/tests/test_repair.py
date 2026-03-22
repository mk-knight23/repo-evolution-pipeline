from __future__ import annotations

import pytest


def test_apply_repair_plan_updates_creates_deletes():
    from pipeline.agents.repair import apply_repair_plan

    files = {
        "package.json": '{"name":"x"}',
        "src/a.ts": "export const a = 1;",
        "src/delete.ts": "bye",
    }

    plan = {
        "edits": [
            {"action": "update", "file_path": "src/a.ts", "content": "export const a = 2;"},
            {"action": "create", "file_path": "src/new.ts", "content": "export const n = 1;"},
            {"action": "delete", "file_path": "src/delete.ts"},
        ]
    }

    out = apply_repair_plan(files, plan)
    assert out["src/a.ts"] == "export const a = 2;"
    assert out["src/new.ts"] == "export const n = 1;"
    assert "src/delete.ts" not in out


@pytest.mark.asyncio
async def test_repair_generated_files_invokes_llm_and_applies(monkeypatch):
    from pipeline.agents.repair import repair_generated_files

    captured: dict[str, object] = {}

    async def fake_invoke_with_retry(*args, **kwargs):
        captured["prompt"] = kwargs.get("prompt") or (args[0] if args else "")
        return {
            "edits": [
                {"action": "update", "file_path": "src/a.ts", "content": "export const a = 2;"},
            ]
        }

    monkeypatch.setattr("pipeline.agents.repair.invoke_with_retry", fake_invoke_with_retry)

    files = {
        "package.json": """{
  "name": "x",
  "version": "1.0.0",
  "scripts": { "type-check": "tsc --noEmit" }
}""",
        "src/a.ts": "export const a = 1;",
    }

    verification_report = {
        "project_dir": "/tmp/x",
        "all_passed": False,
        "failure_category": "types",
        "failure_summary": "Type checking failed",
        "relevant_files": ["src/a.ts"],
        "checks": [
            {
                "name": "type-check",
                "command": "npm run type-check",
                "success": False,
                "exit_code": 2,
                "stdout": "",
                "stderr": "TS error",
                "failure_category": "types",
                "summary": "Type checking failed",
                "relevant_files": ["src/a.ts"],
            }
        ],
    }

    out = await repair_generated_files(files, verification_report, repo_name="x")
    assert out["src/a.ts"] == "export const a = 2;"
    prompt = str(captured["prompt"])
    assert "Primary failure category: types" in prompt
    assert "src/a.ts" in prompt


@pytest.mark.asyncio
async def test_orchestrator_verify_repair_reruns_verification(monkeypatch):
    from pipeline.core.orchestrator import PipelineOrchestrator
    from pipeline.core.models import (
        RepoEvolutionState,
        RepoManifest,
        RepoCategory,
        PipelineStage,
        VerificationReport,
        VerificationCheck,
    )
    from pipeline.core.config import config

    # Enable verification + repair for this test.
    object.__setattr__(config, "verification_enabled", True)
    object.__setattr__(config, "verification_repair_enabled", True)
    object.__setattr__(config, "verification_repair_attempts", 1)
    object.__setattr__(config, "verification_strict", False)

    failing = VerificationReport(
        project_dir="/tmp/fail",
        all_passed=False,
        checks=[
            VerificationCheck(
                name="test",
                command="npm test",
                success=False,
                exit_code=1,
                stdout="",
                stderr="fail",
            )
        ],
    )
    passing = VerificationReport(
        project_dir="/tmp/pass",
        all_passed=True,
        checks=[
            VerificationCheck(
                name="test",
                command="npm test",
                success=True,
                exit_code=0,
                stdout="ok",
                stderr="",
            )
        ],
    )

    calls = {"verify": 0, "repair": 0}

    async def fake_verify_generated_project(*args, **kwargs):
        calls["verify"] += 1
        return failing if calls["verify"] == 1 else passing

    async def fake_repair_generated_files(files, verification_report, repo_name):
        calls["repair"] += 1
        return {**files, "src/fix.ts": "export const fixed = true;"}

    monkeypatch.setattr("pipeline.core.orchestrator.verify_generated_project", fake_verify_generated_project, raising=False)
    monkeypatch.setattr("pipeline.core.orchestrator.VerificationOptions", object, raising=False)
    monkeypatch.setattr("pipeline.core.orchestrator.repair_generated_files", fake_repair_generated_files, raising=False)

    # If the above module-level patch fails (because orchestrator imports inside method),
    # patch the source modules too.
    monkeypatch.setattr("pipeline.quality.verifier.verify_generated_project", fake_verify_generated_project)
    monkeypatch.setattr("pipeline.agents.repair.repair_generated_files", fake_repair_generated_files)

    state = RepoEvolutionState(
        repo_name="x",
        github_url="",
        manifest=RepoManifest(name="x", github_url="", description="", category=RepoCategory.WEBAPP),
        generated_files={"package.json": '{"name":"x","version":"1.0.0","scripts":{"test":"echo ok"}}'},
        stage=PipelineStage.VERIFYING,
    )

    orch = PipelineOrchestrator()
    out = await orch._stage_verify(state)

    assert calls["verify"] == 2
    assert calls["repair"] == 1
    assert out.verification_report is not None
    assert out.verification_report.all_passed is True
    assert "src/fix.ts" in out.generated_files
