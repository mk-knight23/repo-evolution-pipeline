"""Tests for pipeline.core.models — Pydantic v2 domain models."""

import json
from pathlib import Path


from pipeline.core.models import (
    RepoManifest,
    RepoCategory,
    MobileFramework,
    NavigationType,
    PipelineStage,
    ScreenSpec,
    DesignBrief,
    QualityGate,
    QualityGateResult,
    RepoEvolutionState,
)


class TestRepoManifest:
    def test_create_manifest(self, sample_manifest):
        assert sample_manifest.name == "test-portfolio"
        assert sample_manifest.category == RepoCategory.PORTFOLIO
        assert sample_manifest.stars == 42

    def test_manifest_defaults(self):
        m = RepoManifest(
            name="test",
            github_url="https://github.com/u/test",
            description="test",
            category=RepoCategory.WEBAPP,
        )
        assert m.stars == 0
        assert m.language == ""
        assert m.topics == []

    def test_manifest_with_all_fields(self):
        m = RepoManifest(
            name="full-test",
            github_url="https://github.com/u/full-test",
            description="Full test",
            category=RepoCategory.GAME,
            stars=999,
            language="Rust",
            topics=["game", "wasm"],
            has_tests=True,
            has_ci=True,
        )
        assert m.has_tests is True
        assert m.has_ci is True


class TestMobileArchitecture:
    def test_create_architecture(self, sample_architecture):
        assert sample_architecture.framework == MobileFramework.EXPO
        assert len(sample_architecture.screens) == 5
        assert sample_architecture.state_management == "zustand"

    def test_screen_spec(self):
        s = ScreenSpec(name="Home", purpose="Main screen", components=["Header"])
        assert s.name == "Home"
        assert len(s.components) == 1

    def test_architecture_dependencies(self, sample_architecture):
        assert "expo" in sample_architecture.dependencies
        assert "react" in sample_architecture.dependencies


class TestDeepAnalysis:
    def test_create_deep_analysis(self, sample_deep_analysis):
        assert sample_deep_analysis.detected_framework == "Next.js"
        assert sample_deep_analysis.complexity_score == 5
        assert len(sample_deep_analysis.routes_found) == 4


class TestDesignBrief:
    def test_create_design_brief(self):
        brief = DesignBrief(
            app_name="Test App",
            tagline="A test app",
            screens=[ScreenSpec(name="Home", purpose="Main")],
            primary_color="#2563EB",
            navigation_type=NavigationType.TABS,
            key_features=["Dark mode"],
        )
        assert brief.app_name == "Test App"
        assert len(brief.screens) == 1


class TestQualityGate:
    def test_passed_gate(self):
        gate = QualityGate(
            name="test_gate",
            passed=True,
            result=QualityGateResult.PASSED,
            message="All good",
            weight=10,
        )
        assert gate.passed is True
        assert gate.result == QualityGateResult.PASSED

    def test_failed_gate(self):
        gate = QualityGate(
            name="test_gate",
            passed=False,
            result=QualityGateResult.FAILED,
            message="Failed check",
            weight=10,
            is_critical=True,
        )
        assert gate.is_critical is True


class TestRepoEvolutionState:
    def test_create_state(self, sample_manifest):
        state = RepoEvolutionState(
            repo_name=sample_manifest.name,
            github_url=sample_manifest.github_url,
        )
        assert state.stage == PipelineStage.PENDING
        assert state.errors == []

    def test_state_timing(self, sample_manifest):
        state = RepoEvolutionState(
            repo_name=sample_manifest.name,
            github_url=sample_manifest.github_url,
        )
        state.mark_started()
        assert state.started_at is not None
        state.mark_completed()
        assert state.completed_at is not None
        assert state.duration_seconds >= 0

    def test_state_errors(self, sample_manifest):
        state = RepoEvolutionState(
            repo_name=sample_manifest.name,
            github_url=sample_manifest.github_url,
        )
        state.add_error("Test error")
        assert len(state.errors) == 1
        assert state.stage == PipelineStage.FAILED

    def test_stage_execution_journal(self, sample_manifest):
        state = RepoEvolutionState(
            repo_name=sample_manifest.name,
            github_url=sample_manifest.github_url,
        )

        state.record_stage_execution(PipelineStage.CLONING, "started", attempt=1)
        state.record_stage_execution(PipelineStage.CLONING, "completed", attempt=1, duration_seconds=0.42)

        assert len(state.stage_history) == 2
        assert state.stage_history[0].stage == PipelineStage.CLONING
        assert state.stage_history[0].status == "started"
        assert state.stage_history[1].status == "completed"
        assert state.stage_history[1].duration_seconds == 0.42

    def test_checkpoint_roundtrip_with_stage_history(self, sample_manifest, tmp_path):
        state = RepoEvolutionState(
            repo_name=sample_manifest.name,
            github_url=sample_manifest.github_url,
        )
        state.record_stage_execution(PipelineStage.ANALYZING, "completed", attempt=1, duration_seconds=1.2)

        state.checkpoint(data_dir=str(tmp_path))
        loaded = RepoEvolutionState.load_checkpoint(sample_manifest.name, data_dir=str(tmp_path))

        assert loaded is not None
        assert len(loaded.stage_history) == 1
        assert loaded.stage_history[0].stage == PipelineStage.ANALYZING
        assert loaded.stage_history[0].status == "completed"

    def test_checkpoint_write_is_atomic_and_versioned(self, sample_manifest, tmp_path):
        state = RepoEvolutionState(
            repo_name=sample_manifest.name,
            github_url=sample_manifest.github_url,
        )

        state.checkpoint(data_dir=str(tmp_path))

        checkpoint_path = Path(tmp_path) / f"checkpoint-{sample_manifest.name}.json"
        assert checkpoint_path.exists()

        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        assert payload["checkpoint_schema_version"] == RepoEvolutionState.CHECKPOINT_SCHEMA_VERSION

        tmp_files = list(Path(tmp_path).glob(f"checkpoint-{sample_manifest.name}.json.tmp-*"))
        assert tmp_files == []

    def test_load_checkpoint_supports_legacy_payload_without_schema(self, sample_manifest, tmp_path):
        legacy_payload = {
            "repo_name": sample_manifest.name,
            "github_url": sample_manifest.github_url,
            "stage": "pending",
            "errors": [],
            "warnings": [],
            "source_files": {},
            "generated_files": {},
            "should_skip": False,
            "retry_count": 0,
            "duration_seconds": 0.0,
            "stage_history": [],
        }
        checkpoint_path = Path(tmp_path) / f"checkpoint-{sample_manifest.name}.json"
        checkpoint_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

        loaded = RepoEvolutionState.load_checkpoint(sample_manifest.name, data_dir=str(tmp_path))

        assert loaded is not None
        assert loaded.repo_name == sample_manifest.name
        assert loaded.checkpoint_schema_version == RepoEvolutionState.CHECKPOINT_SCHEMA_VERSION


class TestPipelineStages:
    def test_all_stages_exist(self):
        stages = [
            PipelineStage.PENDING,
            PipelineStage.CLONING,
            PipelineStage.ANALYZING,
            PipelineStage.ARCHITECTING,
            PipelineStage.GENERATING,
            PipelineStage.QUALITY_CHECK,
            PipelineStage.PUSHING,
            PipelineStage.COMPLETED,
            PipelineStage.FAILED,
            PipelineStage.SKIPPED,
        ]
        assert len(stages) >= 10
