"""
Domain models for the repo-evolution pipeline.
Strongly typed with Pydantic v2 for runtime validation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field  # type: ignore

logger = logging.getLogger("pipeline.models")



# ── Enums ──────────────────────────────────────────────────────────────────

class RepoCategory(str, Enum):
    PORTFOLIO = "portfolio"
    WEBAPP = "webapp"
    GAME = "game"
    TOOL = "tool"
    STARTER = "starter"
    DASHBOARD = "dashboard"
    ECOMMERCE = "ecommerce"
    SOCIAL = "social"
    BLOG = "blog"
    DOCS = "docs"
    API = "api"
    OTHER = "other"


class MobileFramework(str, Enum):
    EXPO = "expo"
    REACT_NATIVE = "react-native"
    # flutter and ionic are deprecated in v2.1


class ArchitectureStyle(str, Enum):
    MONOLITHIC = "monolithic"
    MICRO_FRONTEND = "micro_frontend"
    WORKSPACE = "workspace"


class NavigationType(str, Enum):
    STACK = "stack"
    TAB = "tab"
    TABS = "tab"  # Alias — agents use TABS
    DRAWER = "drawer"
    HYBRID = "hybrid"


class PipelineStage(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    ARCHITECTING = "architecting"
    GENERATING = "generating"
    VERIFYING = "verifying"
    CI_ATTACHING = "ci_attaching"
    DOCUMENTING = "documenting"
    QUALITY_CHECK = "quality_check"
    PUSHING = "pushing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BuildStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class QualityGateResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


# ── Core Models ────────────────────────────────────────────────────────────

class RepoManifest(BaseModel):
    """Extracted metadata from a GitHub repository."""
    name: str
    github_url: str
    description: str = ""
    language: str = ""
    framework: str = "unknown"
    category: RepoCategory = RepoCategory.OTHER
    features: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    api_endpoints: list[str] = Field(default_factory=list)
    ui_patterns: list[str] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict)
    commit_sha: str = ""
    stars: int = 0
    last_updated: str = ""
    file_count: int = 0
    has_tests: bool = False
    has_ci: bool = False


class DeepAnalysis(BaseModel):
    """Component-level analysis from actual source code."""
    purpose: str = ""
    pages: list[dict] = Field(default_factory=list)
    components: list[dict] = Field(default_factory=list)
    api_calls: list[dict] = Field(default_factory=list)
    data_models: list[Any] = Field(default_factory=list)
    state_shape: dict = Field(default_factory=dict)
    static_data: list[str] = Field(default_factory=list)
    external_deps_that_matter: list[str] = Field(default_factory=list)
    mobile_translation_notes: list[str] = Field(default_factory=list)
    accessibility_notes: list[str] = Field(default_factory=list)
    performance_considerations: list[str] = Field(default_factory=list)
    # Fields returned by LLM analysis and consumed by architect/codegen
    complexity_score: Optional[int] = None
    detected_framework: str = ""
    detected_patterns: list[str] = Field(default_factory=list)
    routes_found: list[str] = Field(default_factory=list)
    state_management: str = ""
    styling_approach: str = ""
    conversion_notes: str = ""
    key_components: list[str] = Field(default_factory=list)
    api_endpoints: list[str] = Field(default_factory=list)
    # V2.1: Design Extraction
    extracted_theme: dict[str, Any] = Field(default_factory=dict)  # hex colors, key theme strings
    # V2.5: Readiness
    readiness_score: int = 5  # 1-10
    critical_roadblocks: list[str] = Field(default_factory=list)


class DesignBrief(BaseModel):
    """Analysis output describing the app's essence."""
    purpose: str = ""
    target_user: str = ""
    core_features: list[str] = Field(default_factory=list)
    ux_flow: list[str] = Field(default_factory=list)
    mobile_enhancements: list[str] = Field(default_factory=list)
    accessibility_requirements: list[str] = Field(default_factory=list)
    performance_targets: dict = Field(default_factory=dict)
    # Fields set by analyzer agent
    app_name: str = ""
    tagline: str = ""
    screens: list[Any] = Field(default_factory=list)  # list[ScreenSpec] (forward ref)
    primary_color: str = "#2563EB"
    navigation_type: Any = None  # NavigationType or None
    key_features: list[str] = Field(default_factory=list)
    extracted_theme: dict[str, Any] = Field(default_factory=dict)
    # V2.5: Readiness
    readiness_score: int = 5  # 1-10
    critical_roadblocks: list[str] = Field(default_factory=list)


class ScreenSpec(BaseModel):
    """Specification for a single mobile screen."""
    name: str
    route: str = ""
    features: list[str] = Field(default_factory=list)
    renders: str = ""
    data_source: str = ""
    has_form: bool = False
    needs_auth: bool = False
    # Fields used by architect/analyzer agents
    purpose: str = ""
    components: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    original_file: str = ""


class MobileArchitecture(BaseModel):
    """Architecture decisions for the mobile version."""
    framework: MobileFramework
    navigation_type: NavigationType
    screens: list[ScreenSpec] = Field(default_factory=list)
    state_management: str = "zustand"
    offline_strategy: str = "cache-first"
    mobile_enhancements: list[str] = Field(default_factory=list)
    design_tokens: Any = Field(default_factory=dict)
    accessibility_level: str = "AA"  # WCAG compliance target
    navigation_library: str = ""
    dependencies: dict[str, str] = Field(default_factory=dict)
    # V2.1: Deployment
    eas_enabled: bool = True
    # V3.0: Premium Design
    has_premium_ui: bool = True
    # V4.0: Enterprise
    architecture_style: ArchitectureStyle = ArchitectureStyle.MONOLITHIC
    data_sanitization_enabled: bool = False


class QualityGate(BaseModel):
    """Individual quality gate result."""
    name: str
    description: str = ""
    result: QualityGateResult
    passed: bool = False
    message: str = ""
    details: str = ""
    weight: int = 10
    is_critical: bool = False
    auto_fixable: bool = False


class GenerationResult(BaseModel):
    """Output of the code generation step."""
    gitlab_repo_url: str = ""
    files_generated: list[str] = Field(default_factory=list)
    total_lines: int = 0
    build_status: BuildStatus = BuildStatus.PENDING
    ci_pipeline_id: Optional[str] = None
    quality_gates: list[QualityGate] = Field(default_factory=list)
    quality_score: float = 0.0  # 0-100


class VerificationCheck(BaseModel):
    """Single verification command execution."""
    name: str
    command: str
    success: bool
    exit_code: int
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    failure_category: str = ""
    summary: str = ""
    relevant_files: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    """Structured report from running local verification commands."""
    project_dir: str = ""
    checks: list[VerificationCheck] = Field(default_factory=list)
    all_passed: bool = False
    first_failed_check: str = ""
    failure_category: str = ""
    failure_summary: str = ""
    relevant_files: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StageExecutionRecord(BaseModel):
    """Execution record for a single stage attempt."""
    stage: PipelineStage
    status: str  # started | completed | failed
    attempt: int = 1
    duration_seconds: float = 0.0
    error: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RepoEvolutionState(BaseModel):
    """Complete state for one repo flowing through the pipeline."""
    # Identity
    repo_name: str
    github_url: str

    # Source data
    source_files: dict[str, str] = Field(default_factory=dict)
    manifest: Optional[RepoManifest] = None
    deep_analysis: Optional[DeepAnalysis] = None
    design_brief: Optional[DesignBrief] = None

    # Architecture
    architecture: Optional[MobileArchitecture] = None

    # Output
    generated_files: dict[str, str] = Field(default_factory=dict)
    generation_result: Optional[GenerationResult] = None
    verification_report: Optional[VerificationReport] = None
    stage_history: list[StageExecutionRecord] = Field(default_factory=list)

    # Control
    stage: PipelineStage = PipelineStage.PENDING
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    should_skip: bool = False
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    correlation_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])  # type: ignore
    checkpoint_schema_version: int = 1

    CHECKPOINT_SCHEMA_VERSION: ClassVar[int] = 1

    def checkpoint(self, data_dir: str = "data"):
        """Save current state to a JSON file using an atomic write."""
        import os

        path = os.path.join(data_dir, f"checkpoint-{self.repo_name.replace('/', '-')}.json")
        os.makedirs(data_dir, exist_ok=True)

        # Keep checkpoints self-describing for future migrations.
        state_to_write = self.model_copy(update={"checkpoint_schema_version": self.CHECKPOINT_SCHEMA_VERSION})
        payload = state_to_write.model_dump_json(indent=2)

        tmp_path = f"{path}.tmp-{uuid.uuid4().hex[:8]}"  # type: ignore
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)
        logger.debug(f"Checkpoint saved for {self.repo_name}")

    @classmethod
    def load_checkpoint(cls, repo_name: str, data_dir: str = "data") -> Optional[RepoEvolutionState]:
        """Load state from a JSON file if it exists."""
        import json
        import os

        path = os.path.join(data_dir, f"checkpoint-{repo_name.replace('/', '-')}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()

            # Accept legacy checkpoints that pre-date schema versioning.
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                schema_version = parsed.get("checkpoint_schema_version", 0)
                if not isinstance(schema_version, int):
                    schema_version = 0
                if schema_version > cls.CHECKPOINT_SCHEMA_VERSION:
                    logger.warning(
                        "Checkpoint schema (%s) is newer than supported (%s) for %s; attempting best-effort load",
                        schema_version,
                        cls.CHECKPOINT_SCHEMA_VERSION,
                        repo_name,
                    )

            return cls.model_validate(parsed)
        except Exception as e:
            logger.warning(f"Failed to load checkpoint for {repo_name}: {e}")
            return None

    def mark_started(self):
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self):
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at is not None and self.completed_at is not None:
            # Explicitly narrow types for the checker
            from typing import cast
            start = cast(datetime, self.started_at)
            end = cast(datetime, self.completed_at)
            self.duration_seconds = (end - start).total_seconds()

    def add_error(self, error: str):
        self.errors.append(error)
        self.stage = PipelineStage.FAILED

    def record_stage_execution(
        self,
        stage: PipelineStage,
        status: str,
        attempt: int = 1,
        duration_seconds: float = 0.0,
        error: str = "",
    ):
        """Append a stage execution event to the journal."""
        self.stage_history.append(
            StageExecutionRecord(  # type: ignore
                stage=stage,
                status=status,  # type: ignore
                attempt=attempt,  # type: ignore
                duration_seconds=duration_seconds,  # type: ignore
                error=error,  # type: ignore
            )
        )


class PipelineRunSummary(BaseModel):
    """Summary of a complete pipeline execution run."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    pipeline_version: str = "3.0.0"
    total_repos: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    total_screens: int = 0
    total_files: int = 0
    total_lines: int = 0
    avg_quality_score: float = 0.0
    estimated_cost_usd: float = 0.0
    repos: dict[str, dict] = Field(default_factory=dict)
