from pathlib import Path

import pytest

from pipeline.quality.verifier import verify_generated_project, VerificationOptions


class _CP:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.mark.asyncio
async def test_verifier_runs_expected_commands_with_lockfile():
    calls: list[list[str]] = []

    def runner(args, cwd, env, timeout_seconds):
        calls.append(args)
        return _CP(returncode=0, stdout="ok", stderr="")

    files = {
        "package.json": """{
  "name": "test-app",
  "version": "1.0.0",
  "scripts": {
    "lint": "echo lint",
    "type-check": "echo type",
    "test": "echo test"
  }
}""",
        "package-lock.json": "{}",
        "src/index.ts": "export const x = 1;",
    }

    report = await verify_generated_project(
        files=files,
        repo_name="test",
        options=VerificationOptions(include_web_export=False, timeout_seconds=5),
        runner=runner,
    )

    assert report.checks
    assert [c.name for c in report.checks] == ["install", "lint", "type-check", "test"]
    assert calls[0][:2] == ["npm", "ci"]
    assert "--legacy-peer-deps" in calls[0]
    assert calls[1][:3] == ["npm", "run", "lint"]
    assert report.all_passed is True


@pytest.mark.asyncio
async def test_verifier_uses_npm_install_without_lockfile():
    calls: list[list[str]] = []

    def runner(args, cwd, env, timeout_seconds):
        calls.append(args)
        return _CP(returncode=0, stdout="ok", stderr="")

    files = {
        "package.json": """{
  "name": "test-app",
  "version": "1.0.0",
  "scripts": { "test": "echo test" }
}""",
        "src/index.ts": "export const x = 1;",
    }

    report = await verify_generated_project(
        files=files,
        repo_name="test2",
        options=VerificationOptions(include_web_export=False, timeout_seconds=5),
        runner=runner,
    )

    assert report.checks[0].name == "install"
    assert calls[0][:2] == ["npm", "install"]
    assert "--legacy-peer-deps" in calls[0]
    assert report.all_passed is True


@pytest.mark.asyncio
async def test_verifier_can_keep_directory_on_failure():
    def runner(args, cwd, env, timeout_seconds):
        return _CP(returncode=1, stdout="nope", stderr="fail")

    dot_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    files = {
        "package.json": """{
  "name": "test-app",
  "version": "1.0.0",
  "scripts": { "test": "echo test" }
}""",
        "assets/icon.png": dot_png,
        "src/index.ts": "export const x = 1;",
    }

    report = await verify_generated_project(
        files=files,
        repo_name="keep",
        options=VerificationOptions(include_web_export=False, timeout_seconds=5, keep_dir_on_failure=True),
        runner=runner,
    )

    assert report.all_passed is False
    assert report.project_dir
    kept = Path(report.project_dir)
    assert kept.exists()
    assert (kept / "assets" / "icon.png").exists()

    # Clean up to avoid leaving temp dirs behind.
    for _ in range(3):
        try:
            import shutil
            shutil.rmtree(kept, ignore_errors=False)
            break
        except Exception:
            pass


@pytest.mark.asyncio
async def test_verifier_classifies_type_check_failures_and_extracts_relevant_files():
    def runner(args, cwd, env, timeout_seconds):
        if args[:3] == ["npm", "run", "type-check"]:
            return _CP(
                returncode=2,
                stdout="",
                stderr="src/a.ts:3:5 - error TS2322: Type 'string' is not assignable to type 'number'",
            )
        return _CP(returncode=0, stdout="ok", stderr="")

    files = {
        "package.json": """{
  "name": "test-app",
  "version": "1.0.0",
  "scripts": { "type-check": "tsc --noEmit" }
}""",
        "src/a.ts": "export const a: number = 'x';",
    }

    report = await verify_generated_project(
        files=files,
        repo_name="typed",
        options=VerificationOptions(include_web_export=False, timeout_seconds=5),
        runner=runner,
    )

    assert report.all_passed is False
    assert report.first_failed_check == "type-check"
    assert report.failure_category == "types"
    assert report.failure_summary == "Type checking failed"
    assert "src/a.ts" in report.relevant_files
