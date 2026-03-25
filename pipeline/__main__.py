"""
CLI Entry Point — Repo Evolution Pipeline v2.0

Usage:
    python -m pipeline run --manifests data/manifests.json
    python -m pipeline run-single --repo "user/repo-name"
    python -m pipeline health
    python -m pipeline quality --files-dir ./output
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# ── Logging Setup ─────────────────────────────────────────────────────────

def setup_logging(verbose: bool = False, json_mode: bool = False):
    from pipeline.core.logging import setup_structured_logging  # type: ignore
    setup_structured_logging(verbose=verbose, json_mode=json_mode)


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_run(manifests_path: str, batch_size: int = 5, max_concurrent: int = 5):
    """Run the full pipeline on a list of repo manifests."""
    from pipeline.core.orchestrator import PipelineOrchestrator  # type: ignore
    from pipeline.core.models import RepoManifest  # type: ignore
    from pipeline.core.config import config  # type: ignore

    config.batch_size = batch_size
    config.max_concurrent = max_concurrent

    # Load manifests
    path = Path(manifests_path)
    if not path.exists():
        print(f"Error: Manifest file not found: {path}")
        sys.exit(1)

    with open(path) as f:
        raw = json.load(f)

    manifests = [RepoManifest(**m) for m in raw]
    print(f"Loaded {len(manifests)} repo manifests from {path}")

    # Run pipeline
    orchestrator = PipelineOrchestrator()
    summary = asyncio.run(orchestrator.run_all(manifests))

    # Save summary
    output_path = Path("data") / "last-run-summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nSummary saved to {output_path}")


def cmd_run_single(repo: str, category: str = "webapp"):
    """Run the pipeline for a single repository."""
    from pipeline.core.orchestrator import PipelineOrchestrator  # type: ignore
    from pipeline.core.models import RepoManifest, RepoCategory  # type: ignore

    cat_map = {c.value: c for c in RepoCategory}
    repo_category = cat_map.get(category, RepoCategory.WEBAPP)

    manifest = RepoManifest(
        name=repo.split("/")[-1],
        github_url=f"https://github.com/{repo}",
        description=f"Mobile conversion of {repo}",
        category=repo_category,
    )

    orchestrator = PipelineOrchestrator()
    state = asyncio.run(orchestrator.run_single(manifest))

    print(f"\nResult: {state.stage.value}")
    if state.errors:
        print(f"Errors: {state.errors}")
    if state.generation_result:
        print(f"Files: {len(state.generation_result.files_generated)}")
        print(f"Quality: {state.generation_result.quality_score:.1f}/100")
        if state.generation_result.gitlab_repo_url:
            print(f"GitLab: {state.generation_result.gitlab_repo_url}")


def cmd_health():
    """Run health checks on all dependencies."""
    from pipeline.monitoring.dashboard import run_health_check  # type: ignore

    print("Running health checks...\n")
    results = run_health_check()

    for check, status in results.items():
        print(f"  {check:<30} {status}")

    all_ok = all("✅" in str(v) for v in results.values())
    print(f"\n{'✅ All checks passed!' if all_ok else '⚠️ Some checks failed — see above'}")


def cmd_quality(files_dir: str):
    """Run quality gates on a directory of generated files."""
    from pipeline.quality.gates import run_quality_gates  # type: ignore
    from pipeline.core.models import MobileArchitecture, MobileFramework, NavigationType, RepoManifest, RepoCategory  # type: ignore

    path = Path(files_dir)
    if not path.is_dir():
        print(f"Error: Directory not found: {path}")
        sys.exit(1)

    # Read all files
    files = {}
    for fp in path.rglob("*"):
        if fp.is_file() and fp.suffix in (".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml", ".md"):
            try:
                files[str(fp.relative_to(path))] = fp.read_text()
            except Exception:
                pass

    # Minimal architecture for quality check
    arch = MobileArchitecture(
        framework=MobileFramework.EXPO,
        navigation_type=NavigationType.TABS,
        screens=[],
        state_management="zustand",
    )
    manifest = RepoManifest(
        name=path.name,
        github_url="",
        description="Quality check",
        category=RepoCategory.WEBAPP,
    )

    gates, score = run_quality_gates(files=files, arch=arch, manifest=manifest)

    print(f"\nQuality Score: {score:.1f}/100\n")
    for gate in gates:
        icon = "✅" if gate.passed else "❌"
        msg = gate.message or gate.details or gate.description
        print(f"  {icon} {gate.name:<35} {msg}")

    print(f"\n{'✅ Quality check passed!' if score >= 60 else '⚠️ Quality below threshold (60)'}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Repo Evolution Pipeline v2.0 — GitHub to GitLab Mobile App Converter",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Machine-readable JSON output")

    sub = parser.add_subparsers(dest="command")

    # run
    run_parser = sub.add_parser("run", help="Run pipeline on manifest file")
    run_parser.add_argument("--manifests", required=True, help="Path to manifests JSON file")
    run_parser.add_argument("--batch-size", type=int, default=5)
    run_parser.add_argument("--max-concurrent", type=int, default=5)

    # run-single
    single_parser = sub.add_parser("run-single", help="Run pipeline for a single repo")
    single_parser.add_argument("--repo", required=True, help="GitHub repo (user/name)")
    single_parser.add_argument("--category", default="webapp", help="Repo category")

    # health
    sub.add_parser("health", help="Run dependency health checks")

    # quality
    quality_parser = sub.add_parser("quality", help="Run quality gates on generated files")
    quality_parser.add_argument("--files-dir", required=True, help="Directory with generated files")

    # version
    sub.add_parser("version", help="Show pipeline version")

    # api
    api_parser = sub.add_parser("api", help="Start the FastAPI server")
    api_parser.add_argument("--host", default="0.0.0.0")
    api_parser.add_argument("--port", type=int, default=8000)
    api_parser.add_argument("--reload", action="store_true")

    args = parser.parse_args()
    setup_logging(args.verbose, getattr(args, 'json_output', False))

    if args.command == "run":
        cmd_run(args.manifests, args.batch_size, args.max_concurrent)
    elif args.command == "run-single":
        cmd_run_single(args.repo, args.category)
    elif args.command == "health":
        cmd_health()
    elif args.command == "quality":
        cmd_quality(args.files_dir)
    elif args.command == "version":
        from pipeline.core.config import config  # type: ignore
        print(f"Repo Evolution Pipeline v{config.pipeline_version}")
    elif args.command == "api":
        import uvicorn  # type: ignore
        uvicorn.run("pipeline.api.server:app", host=args.host, port=args.port, reload=args.reload)  # type: ignore
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
