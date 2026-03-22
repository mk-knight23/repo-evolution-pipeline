"""
Pipeline Orchestrator — parallel processing engine with concurrency control.
Processes repos in configurable batches with error recovery and monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from pipeline.core.config import config
from pipeline.core.models import (
    PipelineStage,
    RepoManifest,
    RepoEvolutionState,
    GenerationResult,
    BuildStatus,
)
from pipeline.core.llm import cost_tracker
from pipeline.core.event_bus import event_bus, PipelineEvent
from pipeline.core.stages import registry, FunctionalStage
from pipeline.monitoring.dashboard import PipelineMonitor

logger = logging.getLogger("pipeline.orchestrator")


class PipelineOrchestrator:
    """Orchestrates the full repo-evolution pipeline with parallel processing."""

    def __init__(self, monitor: Optional[PipelineMonitor] = None):
        self.monitor = monitor or PipelineMonitor(data_dir=config.data_dir)
        self._setup_stages()

    def _setup_stages(self):
        """Register all core stages with the global registry."""
        registry.register(FunctionalStage(PipelineStage.CLONING, self._stage_clone))
        registry.register(FunctionalStage(PipelineStage.ANALYZING, self._stage_analyze))
        registry.register(FunctionalStage(PipelineStage.ARCHITECTING, self._stage_architect))
        registry.register(FunctionalStage(PipelineStage.GENERATING, self._stage_generate))
        registry.register(FunctionalStage(PipelineStage.VERIFYING, self._stage_verify))
        registry.register(FunctionalStage(PipelineStage.QUALITY_CHECK, self._stage_quality_check))
        registry.register(FunctionalStage(PipelineStage.PUSHING, self._stage_push))

    async def run_all(
        self,
        manifests: list[RepoManifest],
        batch_size: Optional[int] = None,
        max_concurrent: Optional[int] = None,
        enabled_stages: Optional[list[str]] = None,
        run_id: str = "",
    ) -> dict:
        """Process all repos in configurable batches with concurrency control."""
        effective_batch_size = batch_size or config.batch_size
        effective_max_concurrent = max_concurrent or config.max_concurrent
        semaphore = asyncio.Semaphore(effective_max_concurrent)

        self.monitor.start_run(total_repos=len(manifests), run_id=run_id)

        # Sort by priority: stars DESC, then updated_at DESC
        sorted_manifests = sorted(
            manifests,
            key=lambda m: (m.stars, m.last_updated),
            reverse=True,
        )

        # Process in batches
        for batch_start in range(0, len(sorted_manifests), effective_batch_size):
            batch = sorted_manifests[batch_start:batch_start + effective_batch_size]
            batch_num = (batch_start // effective_batch_size) + 1
            total_batches = (len(sorted_manifests) + effective_batch_size - 1) // effective_batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} "
                       f"({len(batch)} repos)")

            # Run batch with concurrency control
            tasks = [
                self._process_repo_with_semaphore(manifest, semaphore, enabled_stages)
                for manifest in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results
            for manifest, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Repo {manifest.name} failed: {result}")
                    state = RepoEvolutionState(
                        repo_name=manifest.name,
                        github_url=manifest.github_url,
                        stage=PipelineStage.FAILED,
                        errors=[str(result)],
                    )
                    self.monitor.update_repo(state)

            self.monitor.print_progress()

        # Generate final report
        summary = self.monitor.generate_summary(cost_tracker.summary())
        return summary.model_dump()

    async def run_single(
        self,
        manifest: RepoManifest,
        enabled_stages: Optional[list[str]] = None,
        run_id: str = "",
    ) -> RepoEvolutionState:
        """Process a single repo through the full pipeline."""
        if not self.monitor.started_at:
            self.monitor.start_run(total_repos=1, run_id=run_id)
        return await self._process_repo(manifest, enabled_stages=enabled_stages)

    async def _process_repo_with_semaphore(
        self,
        manifest: RepoManifest,
        semaphore: asyncio.Semaphore,
        enabled_stages: Optional[list[str]] = None,
    ) -> RepoEvolutionState:
        """Process a repo with concurrency limiting."""
        async with semaphore:
            self.monitor.in_progress += 1
            try:
                result = await self._process_repo(manifest, enabled_stages=enabled_stages)
                return result
            finally:
                self.monitor.in_progress -= 1

    async def _process_repo(
        self,
        manifest: RepoManifest,
        retry_count: int = 0,
        enabled_stages: Optional[list[str]] = None,
    ) -> RepoEvolutionState:
        """Execute the full pipeline for a single repo using the stage registry with checkpointing."""
        current_retry = retry_count
        
        while current_retry <= config.max_retries:
            # Attempt to resume from checkpoint
            checkpoint_state = RepoEvolutionState.load_checkpoint(manifest.name, config.data_dir)
            if checkpoint_state and checkpoint_state.stage == PipelineStage.COMPLETED:
                logger.info(f"Skipping {manifest.name} — already completed (loaded from checkpoint)")
                self.monitor.update_repo(checkpoint_state)
                return checkpoint_state

            state = checkpoint_state or RepoEvolutionState(
                repo_name=manifest.name,
                github_url=manifest.github_url,
                manifest=manifest,
                retry_count=current_retry,
            )
            
            if not state.started_at:
                state.mark_started()

            # Build list of stages to run based on config
            enabled_names = list(enabled_stages) if enabled_stages is not None else list(config.enabled_stages)
            
            # Special case for verification (which has its own config flag)
            if not config.verification_enabled and "verifying" in enabled_names:
                enabled_names = [n for n in enabled_names if n != "verifying"]

            try:
                # Resolve stages from registry
                stages_to_run = []
                for name_str in enabled_names:
                    try:
                        stage_enum = PipelineStage(name_str)
                        stage = registry.get(stage_enum)
                        if stage:
                            stages_to_run.append(stage)
                    except ValueError:
                        logger.warning(f"Unknown stage name in config: {name_str}")

                # Track which stage we are resuming from
                completed_stage_names = {
                    record.stage
                    for record in state.stage_history
                    if record.status == "completed"
                }

                for stage in stages_to_run:
                    # Preferred resume strategy: explicit stage journal.
                    if checkpoint_state and stage.name in completed_stage_names:
                        logger.info(f"Resuming {manifest.name}: skipping {stage.name.value} (already completed)")
                        continue

                    # Backward-compatibility fallback for legacy checkpoints.
                    if checkpoint_state and not completed_stage_names:
                        # Very simple resume logic: if we have files generated, skip up to GENERATING
                        if stage.name == PipelineStage.CLONING and state.source_files:
                            logger.info(f"Resuming {manifest.name}: skipping {stage.name.value}")
                            continue
                        if stage.name == PipelineStage.ANALYZING and state.deep_analysis:
                            logger.info(f"Resuming {manifest.name}: skipping {stage.name.value}")
                            continue
                        if stage.name == PipelineStage.ARCHITECTING and state.architecture:
                            logger.info(f"Resuming {manifest.name}: skipping {stage.name.value}")
                            continue
                        if stage.name == PipelineStage.GENERATING and state.generated_files:
                            logger.info(f"Resuming {manifest.name}: skipping {stage.name.value}")
                            continue

                    # Update state and emit events
                    state.stage = stage.name
                    state.record_stage_execution(
                        stage=stage.name,
                        status="started",
                        attempt=current_retry + 1,
                    )
                    await event_bus.emit(PipelineEvent.STAGE_STARTED, {
                        "run_id": self.monitor.run_id,
                        "correlation_id": state.correlation_id,
                        "stage": stage.name,
                        "repo": manifest.name,
                        "attempt": current_retry + 1,
                    })
                    
                    t0 = time.time()
                    state = await stage.run(state)
                    duration = time.time() - t0
                    state.record_stage_execution(
                        stage=stage.name,
                        status="completed",
                        attempt=current_retry + 1,
                        duration_seconds=duration,
                    )
                    
                    self.monitor.record_stage_time(manifest.name, stage.name.value, duration)
                    await event_bus.emit(PipelineEvent.STAGE_COMPLETED, {
                        "run_id": self.monitor.run_id,
                        "correlation_id": state.correlation_id,
                        "stage": stage.name,
                        "repo": manifest.name,
                        "attempt": current_retry + 1,
                        "duration_seconds": duration,
                    })

                    # Save checkpoint after each successful stage
                    state.checkpoint(config.data_dir)

                    # Strict verification check (legacy logic preservation)
                    if stage.name == PipelineStage.VERIFYING and config.verification_strict:
                        if state.verification_report and not state.verification_report.all_passed:
                            state.add_error("Verification failed (strict mode enabled)")
                            break

                    # Check if we should stop early
                    if state.stage == PipelineStage.FAILED:
                        break
                    if state.should_skip:
                        state.stage = PipelineStage.SKIPPED
                        break

                if state.stage == PipelineStage.SKIPPED:
                    state.mark_completed()
                    state.checkpoint(config.data_dir)
                    self.monitor.update_repo(state)
                    logger.info(f"⏭ {manifest.name} skipped in {state.duration_seconds:.1f}s")
                    return state

                # Mark success if not failed
                if state.stage != PipelineStage.FAILED:
                    state.stage = PipelineStage.COMPLETED
                    state.mark_completed()
                    # Final checkpoint for completed state
                    state.checkpoint(config.data_dir)
                    self.monitor.update_repo(state)
                    logger.info(f"✅ {manifest.name} completed in {state.duration_seconds:.1f}s")
                    return state

            except Exception as e:
                await event_bus.emit(PipelineEvent.STAGE_FAILED, {
                    "run_id": self.monitor.run_id,
                    "correlation_id": state.correlation_id,
                    "stage": state.stage,
                    "repo": manifest.name,
                    "attempt": current_retry + 1,
                    "error": str(e),
                })
                if isinstance(state.stage, PipelineStage):
                    state.record_stage_execution(
                        stage=state.stage,
                        status="failed",
                        attempt=current_retry + 1,
                        error=str(e),
                    )
                state.add_error(str(e))
                state.mark_completed()
                logger.error(f"❌ {manifest.name} failed: {e}")

                # Retry logic
                current_retry += 1
                if current_retry <= config.max_retries:
                    logger.info(f"Retrying {manifest.name} (attempt {current_retry}/{config.max_retries})")
                    # Small delay before retry
                    await asyncio.sleep(1)
                    continue
                else:
                    break

        self.monitor.update_repo(state)
        return state


    # ── Pipeline Stages (stubs — delegate to agent modules) ────────────

    async def _stage_clone(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Clone repo and read source files."""
        from pipeline.agents.scanner import deep_clone_and_read
        source_files = deep_clone_and_read(
            state.repo_name,
            github_url=state.github_url,
            commit_sha=state.manifest.commit_sha if state.manifest else "",
        )
        state.source_files = source_files
        if not source_files:
            state.warnings.append("No source files found — will use shallow analysis")
        return state

    async def _stage_analyze(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Analyze repo source code with LLM."""
        from pipeline.agents.analyzer import analyze_repo_deep, analyze_repo_shallow
        from pipeline.core.models import DeepAnalysis

        if state.source_files:
            analysis_dict = await analyze_repo_deep(state.manifest, state.source_files)
            if analysis_dict:
                # Sanitize list[dict] fields — LLM may return strings instead of dicts
                for field_name in ("pages", "components", "api_calls", "data_models"):
                    if field_name in analysis_dict and isinstance(analysis_dict[field_name], list):
                        analysis_dict[field_name] = [
                            item if isinstance(item, dict) else {"name": str(item)}
                            for item in analysis_dict[field_name]
                        ]
                try:
                    state.deep_analysis = DeepAnalysis(**analysis_dict)
                except Exception as e:
                    logger.warning(f"DeepAnalysis validation failed, using raw dict: {e}")
                    # Store what we can even if schema doesn't match perfectly
                    state.deep_analysis = DeepAnalysis(
                        purpose=analysis_dict.get("purpose", analysis_dict.get("conversion_notes", "")),
                    )
        else:
            brief = await analyze_repo_shallow(state.manifest)
            state.design_brief = brief

        return state

    async def _stage_architect(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Design mobile architecture."""
        from pipeline.agents.architect import design_architecture

        state.architecture = design_architecture(
            manifest=state.manifest,
            deep_analysis=state.deep_analysis,
            design_brief=state.design_brief,
        )
        return state

    async def _stage_generate(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Generate mobile app code."""
        from pipeline.agents.codegen import generate_mobile_code

        state.generated_files = await generate_mobile_code(
            manifest=state.manifest,
            architecture=state.architecture,
            source_files=state.source_files,
            deep_analysis=state.deep_analysis,
        )
        return state

    async def _stage_quality_check(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Run quality gates on generated code."""
        from pipeline.quality.gates import run_quality_gates

        gates, score = run_quality_gates(
            files=state.generated_files,
            arch=state.architecture,
            manifest=state.manifest,
        )

        build_status = BuildStatus.PENDING
        if state.verification_report is not None:
            build_status = BuildStatus.SUCCESS if state.verification_report.all_passed else BuildStatus.FAILED

        state.generation_result = GenerationResult(
            files_generated=list(state.generated_files.keys()),
            total_lines=sum(c.count('\n') for c in state.generated_files.values()),
            quality_gates=gates,
            quality_score=score,
            build_status=build_status,
        )
        return state

    async def _stage_verify(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Run real verification commands against the generated project."""
        from pipeline.quality.verifier import verify_generated_project, VerificationOptions
        from pipeline.agents.repair import repair_generated_files

        options = VerificationOptions(
            include_web_export=config.verification_include_web_export,
            timeout_seconds=config.verification_timeout_seconds,
            keep_dir_on_failure=not config.verification_strict,
        )

        report = await verify_generated_project(
            files=state.generated_files,
            repo_name=state.repo_name,
            options=options,
        )

        # Optional: one (or more) repair attempts.
        if (
            (not report.all_passed)
            and config.verification_repair_enabled
            and config.verification_repair_attempts > 0
        ):
            attempts = max(1, config.verification_repair_attempts)
            for _ in range(attempts):
                state.generated_files = await repair_generated_files(
                    state.generated_files,
                    report,
                    repo_name=state.repo_name,
                )
                report = await verify_generated_project(
                    files=state.generated_files,
                    repo_name=state.repo_name,
                    options=options,
                )
                if report.all_passed:
                    break

        state.verification_report = report
        if not report.all_passed:
            state.warnings.append("Verification failed (see verification_report)")
        return state

    async def _stage_push(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Push generated code to GitLab."""
        from pipeline.agents.pusher import push_to_gitlab

        if (
            config.verification_enabled
            and config.block_push_on_verification_failure
            and state.verification_report is not None
            and not state.verification_report.all_passed
        ):
            state.warnings.append("Skipping GitLab push due to verification failure")
            return state

        gitlab_url = await push_to_gitlab(
            manifest=state.manifest,
            architecture=state.architecture,
            files=state.generated_files,
            design_brief=state.design_brief,
        )
        if state.generation_result:
            state.generation_result.gitlab_repo_url = gitlab_url

        return state
