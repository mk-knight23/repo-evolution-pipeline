"""Tests for pipeline.quality.gates — quality gates engine."""


from pipeline.quality.gates import QualityGatesEngine, run_quality_gates


class TestQualityGatesEngine:
    def test_engine_creation(self, sample_generated_files, sample_architecture, sample_manifest):
        engine = QualityGatesEngine(
            files=sample_generated_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        assert engine is not None

    def test_valid_project_structure(self, sample_generated_files, sample_architecture, sample_manifest):
        gates, score = run_quality_gates(
            files=sample_generated_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        # Should have multiple gates
        assert len(gates) > 0
        # Score should be positive
        assert score >= 0

    def test_empty_files_low_score(self, sample_architecture, sample_manifest):
        gates, score = run_quality_gates(
            files={},
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        assert score < 50

    def test_no_hardcoded_secrets_passes(self, sample_generated_files, sample_architecture, sample_manifest):
        gates, _ = run_quality_gates(
            files=sample_generated_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        secret_gate = next((g for g in gates if g.name == "no_hardcoded_secrets"), None)
        assert secret_gate is not None
        assert secret_gate.passed is True

    def test_hardcoded_secrets_detected(self, sample_generated_files, sample_architecture, sample_manifest):
        # Inject a secret
        bad_files = {**sample_generated_files}
        bad_files["src/config.ts"] = 'const API_KEY = "sk-ant-api03-secret12345";'

        gates, _ = run_quality_gates(
            files=bad_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        secret_gate = next((g for g in gates if g.name == "no_hardcoded_secrets"), None)
        assert secret_gate is not None
        assert secret_gate.passed is False

    def test_readme_exists_gate(self, sample_generated_files, sample_architecture, sample_manifest):
        gates, _ = run_quality_gates(
            files=sample_generated_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        readme_gate = next((g for g in gates if g.name == "readme_exists"), None)
        assert readme_gate is not None
        assert readme_gate.passed is True

    def test_missing_readme_fails(self, sample_architecture, sample_manifest):
        files = {"src/app.tsx": "export default function App() {}"}
        gates, _ = run_quality_gates(
            files=files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        readme_gate = next((g for g in gates if g.name == "readme_exists"), None)
        assert readme_gate is not None
        assert readme_gate.passed is False

    def test_ci_yaml_gate(self, sample_generated_files, sample_architecture, sample_manifest):
        gates, _ = run_quality_gates(
            files=sample_generated_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        ci_gate = next((g for g in gates if g.name == "valid_ci_yaml"), None)
        assert ci_gate is not None
        assert ci_gate.passed is True

    def test_quality_score_range(self, sample_generated_files, sample_architecture, sample_manifest):
        _, score = run_quality_gates(
            files=sample_generated_files,
            arch=sample_architecture,
            manifest=sample_manifest,
        )
        assert 0 <= score <= 100
