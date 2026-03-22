"""
Generated Project Verifier — materializes the generated file map to disk and runs
real-world checks (install/lint/typecheck/tests/build) to validate the output.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from pipeline.core.config import config
from pipeline.core.models import VerificationCheck, VerificationReport

logger = logging.getLogger("pipeline.verifier")


def _extract_relevant_files(output: str) -> list[str]:
    """Best-effort extraction of file paths from tool output."""
    patterns = [
        r"([A-Za-z0-9_./-]+\.(?:ts|tsx|js|jsx|json|md|yml|yaml|mjs|cjs))",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(re.findall(pattern, output))

    unique: list[str] = []
    for match in matches:
        if match not in unique:
            unique.append(match)
    return unique[:10]


def _classify_failure(name: str, exit_code: int, stdout: str, stderr: str) -> tuple[str, str, list[str]]:
    """Classify a failed verification check into a repair-friendly taxonomy."""
    merged = f"{stderr}\n{stdout}".lower()
    relevant_files = _extract_relevant_files(f"{stderr}\n{stdout}")

    if exit_code == 124 or "timeout" in merged:
        return "timeout", "Verification command timed out", relevant_files
    if name == "install":
        if any(token in merged for token in ["eai_again", "network", "socket", "fetch", "etimedout"]):
            return "infrastructure", "Dependency install failed due to network or registry issue", relevant_files
        return "dependencies", "Dependency installation failed", relevant_files
    if name == "lint":
        return "lint", "Linting failed", relevant_files
    if name == "type-check":
        return "types", "Type checking failed", relevant_files
    if name == "test":
        return "tests", "Tests failed", relevant_files
    if name == "web-export":
        return "build", "Web export/build failed", relevant_files
    return "verification", f"{name} failed", relevant_files


def _default_runner(args: list[str], cwd: Path, env: dict[str, str], timeout_seconds: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def _write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_png(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(content))


def _materialize_project(files: dict[str, str], root: Path) -> None:
    for rel_path, content in files.items():
        out_path = root / rel_path
        if rel_path.endswith(".png"):
            _write_png(out_path, content)
        else:
            _write_file(out_path, content)


def _write_report_file(project_dir: Path, report: VerificationReport) -> None:
    try:
        out_dir = project_dir / ".pipeline"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "verification-report.json").write_text(
            json.dumps(report.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug(f"Failed to write verification report file: {e}")


def _read_package_scripts(project_dir: Path) -> dict[str, str]:
    pkg_path = project_dir / "package.json"
    if not pkg_path.exists():
        return {}
    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        return scripts if isinstance(scripts, dict) else {}
    except Exception:
        return {}


@dataclass(frozen=True)
class VerificationOptions:
    include_web_export: bool = False
    timeout_seconds: int = 900
    keep_dir_on_failure: bool = False


async def verify_generated_project(
    files: dict[str, str],
    repo_name: str,
    *,
    options: Optional[VerificationOptions] = None,
    runner: Callable[[list[str], Path, dict[str, str], int], subprocess.CompletedProcess] = _default_runner,
) -> VerificationReport:
    """
    Materialize the generated file map and run checks.

    This function is designed to be safe for unit testing: pass a mocked `runner`.
    """
    options = options or VerificationOptions(
        include_web_export=config.verification_include_web_export,
        timeout_seconds=config.verification_timeout_seconds,
    )

    tmp_root = Path(tempfile.mkdtemp(prefix=f"repo-evo-verify-{repo_name}-"))
    project_dir = tmp_root

    skip_cleanup = False
    try:
        _materialize_project(files, project_dir)
        scripts = _read_package_scripts(project_dir)

        env = dict(os.environ)
        env["CI"] = "true"

        checks: list[VerificationCheck] = []

        def run_check(name: str, cmd: list[str]) -> VerificationCheck:
            t0 = time.time()
            try:
                cp = runner(cmd, project_dir, env, options.timeout_seconds)
                duration = time.time() - t0
                success = cp.returncode == 0
                category = ""
                summary = ""
                relevant_files: list[str] = []
                if not success:
                    category, summary, relevant_files = _classify_failure(name, int(cp.returncode), cp.stdout or "", cp.stderr or "")
                return VerificationCheck(
                    name=name,
                    command=" ".join(cmd),
                    success=success,
                    exit_code=int(cp.returncode),
                    duration_seconds=duration,
                    stdout=(cp.stdout or "")[:50_000],
                    stderr=(cp.stderr or "")[:50_000],
                    failure_category=category,
                    summary=summary,
                    relevant_files=relevant_files,
                )
            except subprocess.TimeoutExpired as e:
                duration = time.time() - t0
                stdout = (getattr(e, "stdout", "") or "")[:50_000]
                stderr = (getattr(e, "stderr", "") or f"Timeout after {options.timeout_seconds}s")[:50_000]
                category, summary, relevant_files = _classify_failure(name, 124, stdout, stderr)
                return VerificationCheck(
                    name=name,
                    command=" ".join(cmd),
                    success=False,
                    exit_code=124,
                    duration_seconds=duration,
                    stdout=stdout,
                    stderr=stderr,
                    failure_category=category,
                    summary=summary,
                    relevant_files=relevant_files,
                )

        # Install (best-effort: without lockfile we still try npm ci which may fail)
        if (project_dir / "package-lock.json").exists():
            checks.append(run_check("install", ["npm", "ci", "--legacy-peer-deps", "--prefer-offline", "--no-audit"]))
        else:
            checks.append(run_check("install", ["npm", "install", "--legacy-peer-deps", "--prefer-offline", "--no-audit"]))

        if "lint" in scripts:
            checks.append(run_check("lint", ["npm", "run", "lint"]))
        if "type-check" in scripts:
            checks.append(run_check("type-check", ["npm", "run", "type-check"]))
        if "test" in scripts:
            checks.append(run_check("test", ["npm", "test"]))

        if options.include_web_export:
            # Only attempt if expo appears present.
            pkg = (project_dir / "package.json").read_text(encoding="utf-8", errors="ignore") if (project_dir / "package.json").exists() else ""
            if '"expo"' in pkg or "'expo'" in pkg:
                checks.append(run_check("web-export", ["npx", "expo", "export", "--platform", "web"]))

        all_passed = all(c.success for c in checks) if checks else False
        failed_checks = [c for c in checks if not c.success]
        first_failed = failed_checks[0] if failed_checks else None
        report_relevant_files: list[str] = []
        for check in failed_checks:
            for file_path in check.relevant_files:
                if file_path not in report_relevant_files:
                    report_relevant_files.append(file_path)
        report = VerificationReport(
            project_dir=str(project_dir),
            checks=checks,
            all_passed=all_passed,
            first_failed_check=first_failed.name if first_failed else "",
            failure_category=first_failed.failure_category if first_failed else "",
            failure_summary=first_failed.summary if first_failed else "",
            relevant_files=report_relevant_files[:10],
        )
        _write_report_file(project_dir, report)

        if not report.all_passed:
            failed = [c for c in report.checks if not c.success]
            if failed:
                top = failed[0]
                logger.warning(
                    f"Verification failed at '{top.name}' (exit {top.exit_code}). "
                    f"First stderr line: {(top.stderr.splitlines()[:1] or [''])[0][:200]}"
                )

        if (not report.all_passed) and options.keep_dir_on_failure:
            logger.warning(f"Verification failed; keeping project dir at {project_dir}")
            skip_cleanup = True
        return report
    finally:
        if not skip_cleanup:
            shutil.rmtree(tmp_root, ignore_errors=True)
