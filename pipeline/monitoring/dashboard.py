"""
Pipeline Monitoring & Observability Dashboard
Real-time progress tracking, health metrics, and cost reporting.
"""

from __future__ import annotations

import json
import time
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pipeline.core.models import (
    PipelineStage,
    RepoEvolutionState,
    PipelineRunSummary,
)

logger = logging.getLogger("pipeline.monitor")


# ── ANSI Colors ────────────────────────────────────────────────────────────

class C:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ── Pipeline Monitor ──────────────────────────────────────────────────────

@dataclass
class PipelineMonitor:
    """Central monitoring hub for pipeline execution."""

    run_id: str = ""
    started_at: Optional[datetime] = None
    data_dir: Path = field(default_factory=lambda: Path("data"))

    # Counters
    total_repos: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    in_progress: int = 0

    # Aggregated metrics
    total_screens: int = 0
    total_files: int = 0
    total_lines: int = 0
    avg_quality_score: float = 0.0
    quality_scores: list = field(default_factory=list)

    # Per-repo tracking
    repos: dict = field(default_factory=dict)

    # Timing
    stage_timings: dict = field(default_factory=dict)

    def start_run(self, total_repos: int, run_id: str = ""):
        """Initialize a new pipeline run."""
        self.run_id = run_id or f"run-{int(time.time())}"
        self.started_at = datetime.now(timezone.utc)
        self.total_repos = total_repos
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.in_progress = 0
        self.repos = {}

        logger.info(f"Pipeline run {self.run_id} started — {total_repos} repos to process")
        self._print_header()

    def update_repo(self, state: RepoEvolutionState):
        """Update tracking for a single repo."""
        self.repos[state.repo_name] = {
            "stage": state.stage.value,
            "errors": state.errors,
            "warnings": state.warnings,
            "framework": state.architecture.framework.value if state.architecture else "",
            "category": state.manifest.category.value if state.manifest else "",
            "screens": len(state.architecture.screens) if state.architecture else 0,
            "files": len(state.generated_files),
            "quality_score": state.generation_result.quality_score if state.generation_result else 0,
            "duration": state.duration_seconds,
            "gitlab_url": state.generation_result.gitlab_repo_url if state.generation_result else "",
        }

        # Update counters
        if state.stage == PipelineStage.COMPLETED:
            self.completed += 1
            if state.generation_result:
                self.total_screens += len(state.architecture.screens) if state.architecture else 0
                self.total_files += len(state.generated_files)
                self.quality_scores.append(state.generation_result.quality_score)
                self.avg_quality_score = sum(self.quality_scores) / len(self.quality_scores)
        elif state.stage == PipelineStage.FAILED:
            self.failed += 1
        elif state.stage == PipelineStage.SKIPPED:
            self.skipped += 1

        self._save_state()

    def record_stage_time(self, repo_name: str, stage: str, duration_seconds: float):
        """Record timing for a pipeline stage."""
        if stage not in self.stage_timings:
            self.stage_timings[stage] = []
        self.stage_timings[stage].append(duration_seconds)

    def print_progress(self):
        """Print current progress to terminal."""
        processed = self.completed + self.failed + self.skipped
        bar = self._progress_bar(processed, self.total_repos)

        print(f"\n{C.CYAN}{C.BOLD}{'━' * 60}{C.RESET}")
        print(f"{C.CYAN}  🧬 REPO EVOLUTION PROGRESS{C.RESET}")
        print(f"{C.CYAN}{'━' * 60}{C.RESET}")
        print(f"  {bar}")
        print(f"  {C.GREEN}Completed: {self.completed}{C.RESET}  "
              f"{C.RED}Failed: {self.failed}{C.RESET}  "
              f"{C.YELLOW}Skipped: {self.skipped}{C.RESET}  "
              f"{C.BLUE}In Progress: {self.in_progress}{C.RESET}")
        print(f"  {C.DIM}Screens: {self.total_screens}  "
              f"Files: {self.total_files}  "
              f"Avg Quality: {self.avg_quality_score:.1f}/100{C.RESET}")

        if self.stage_timings:
            print(f"\n  {C.BOLD}Stage Avg Times:{C.RESET}")
            for stage, times in self.stage_timings.items():
                avg = sum(times) / len(times)
                print(f"    {stage:<20} {avg:.1f}s avg ({len(times)} runs)")

        # Show last completed
        last_completed = [
            (name, info) for name, info in self.repos.items()
            if info["stage"] == "completed"
        ]
        if last_completed:
            name, info = last_completed[-1]
            print(f"\n  {C.GREEN}Last: {name} → {info.get('framework', '?')} "
                  f"({info.get('screens', 0)} screens, quality: {info.get('quality_score', 0):.0f}){C.RESET}")

        # Show failures
        failures = [(name, info) for name, info in self.repos.items() if info["stage"] == "failed"]
        if failures:
            print(f"\n  {C.RED}Failures:{C.RESET}")
            from typing import cast
            for name, info in cast(list, failures)[:3]:
                err = info.get("errors", ["unknown"])[-1] if info.get("errors") else "unknown"
                print(f"    {C.RED}✗ {name}: {err[:60]}{C.RESET}")

        print(f"{C.CYAN}{'━' * 60}{C.RESET}\n")

    def generate_summary(self, cost_summary: Optional[dict] = None) -> PipelineRunSummary:
        """Generate final run summary."""
        elapsed = 0.0
        if self.started_at:
            from typing import cast
            elapsed = (datetime.now(timezone.utc) - cast(datetime, self.started_at)).total_seconds()

        summary = PipelineRunSummary(
            run_id=self.run_id,
            started_at=self.started_at or datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            total_repos=self.total_repos,
            completed=self.completed,
            failed=self.failed,
            skipped=self.skipped,
            total_screens=self.total_screens,
            total_files=self.total_files,
            avg_quality_score=self.avg_quality_score,
            estimated_cost_usd=cost_summary.get("total_cost_usd", 0) if cost_summary else 0,
            repos=self.repos,
        )

        # Save final report
        report_path = self.data_dir / f"report-{self.run_id}.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary.model_dump(), indent=2, default=str))
        logger.info(f"Final report saved to {report_path}")

        self._print_final_report(summary, cost_summary, elapsed)
        return summary

    # ── Private Helpers ────────────────────────────────────────────────────

    def _print_header(self):
        from pipeline.core.config import config
        print(f"\n{C.PURPLE}{C.BOLD}{'═' * 60}{C.RESET}")
        print(f"{C.PURPLE}  🧬 REPO EVOLUTION PIPELINE v{config.pipeline_version}{C.RESET}")
        print(f"{C.PURPLE}  Run ID: {self.run_id}{C.RESET}")
        print(f"{C.PURPLE}  Repos: {self.total_repos}{C.RESET}")
        print(f"{C.PURPLE}{'═' * 60}{C.RESET}\n")

    def _print_final_report(self, summary: PipelineRunSummary, cost: dict, elapsed: float):
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)

        print(f"\n{C.GREEN}{C.BOLD}{'═' * 60}{C.RESET}")
        print(f"{C.GREEN}  🧬 REPO EVOLUTION — FINAL REPORT{C.RESET}")
        print(f"{C.GREEN}{'═' * 60}{C.RESET}")
        print(f"  Run: {summary.run_id}")
        print(f"  Duration: {mins}m {secs}s")
        print("")
        print(f"  {C.GREEN}Completed: {summary.completed}/{summary.total_repos}{C.RESET}")
        print(f"  {C.RED}Failed: {summary.failed}{C.RESET}")
        print(f"  {C.YELLOW}Skipped: {summary.skipped}{C.RESET}")
        print(f"  Screens: {summary.total_screens}")
        print(f"  Files: {summary.total_files}")
        print(f"  Avg Quality: {summary.avg_quality_score:.1f}/100")

        if cost:
            print(f"\n  {C.BOLD}Cost Breakdown:{C.RESET}")
            for stage, amount in cost.get("cost_by_stage", {}).items():
                print(f"    {stage:<20} ${amount:.4f}")
            print(f"    {'─' * 30}")
            print(f"    {C.BOLD}TOTAL: ${cost.get('total_cost_usd', 0):.4f}{C.RESET}")

        # Category breakdown
        from typing import Dict, Set, Union
        categories: Dict[str, Dict[str, Union[int, Set[str]]]] = {}
        for name, info in self.repos.items():
            cat = info.get("category", "other")
            if cat not in categories:
                categories[cat] = {"count": 0, "frameworks": set(), "screens": 0}
            
            cat_data = categories[cat]
            from typing import cast
            cat_data["count"] = cast(int, cat_data["count"]) + 1
            cast(set, cat_data["frameworks"]).add(info.get("framework", "?"))
            cat_data["screens"] = cast(int, cat_data["screens"]) + info.get("screens", 0)

        if categories:
            print(f"\n  {C.BOLD}By Category:{C.RESET}")
            print(f"    {'Category':<12} {'Count':>5} {'Framework':<15} {'Screens':>7}")
            print(f"    {'─' * 45}")
            for cat, data in sorted(categories.items()):
                from typing import Iterable
                fw = ", ".join(cast(Iterable[str], data["frameworks"]))
                print(f"    {cat:<12} {data['count']:>5} {fw:<15} {data['screens']:>7}")

        # SLO compliance
        if self.stage_timings:
            slo_target_minutes = 10  # Target: complete each repo within 10 min
            all_durations = []
            for stage_times in self.stage_timings.values():
                all_durations.extend(stage_times)
            if all_durations:
                within_slo = sum(1 for d in all_durations if d <= slo_target_minutes * 60)
                compliance = (within_slo / len(all_durations)) * 100
                print(f"\n  {C.BOLD}SLO Compliance:{C.RESET}")
                print(f"    {compliance:.0f}% of stages completed within {slo_target_minutes}min target")

        print(f"{C.GREEN}{'═' * 60}{C.RESET}\n")

    def _save_state(self):
        """Persist current state to disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "run_id": self.run_id,
            "total_repos": self.total_repos,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "in_progress": self.in_progress,
            "repos": self.repos,
        }
        (self.data_dir / "evolution-status.json").write_text(
            json.dumps(state, indent=2, default=str)
        )

    @staticmethod
    def _progress_bar(current: int, total: int, width: int = 30) -> str:
        filled = int(width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)
        pct = (current / total * 100) if total > 0 else 0
        return f"[{bar}] {current}/{total} ({pct:.0f}%)"


# ── Health Check ───────────────────────────────────────────────────────────

def run_health_check() -> dict:
    """Run a health check on all pipeline dependencies."""
    results = {}

    # Check Python packages
    packages = ["langchain_anthropic", "github", "gitlab", "pydantic", "jinja2", "rich"]
    for pkg in packages:
        try:
            __import__(pkg)
            results[pkg] = "✅ installed"
        except ImportError:
            results[pkg] = "❌ missing"

    # Check environment variables
    env_vars = {
        "ANTHROPIC_API_KEY": bool(len(import_os().environ.get("ANTHROPIC_API_KEY", "")) > 10),
        "GITHUB_TOKEN": bool(len(import_os().environ.get("GITHUB_TOKEN", "")) > 10),
        "GITLAB_TOKEN": bool(len(import_os().environ.get("GITLAB_TOKEN", "")) > 10),
    }
    for var, present in env_vars.items():
        results[var] = "✅ set" if present else "⚠️ not set"

    return results


def import_os():
    import os
    return os
