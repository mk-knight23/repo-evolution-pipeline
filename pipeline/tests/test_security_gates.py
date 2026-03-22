import json
from pipeline.quality.gates import QualityGatesEngine, QualityGateResult
from pipeline.core.models import MobileArchitecture, RepoManifest, MobileFramework, RepoCategory, NavigationType

def test_security_sca_gate():
    # Setup mock architecture and manifest
    arch = MobileArchitecture(
        framework=MobileFramework.EXPO,
        screens=[],
        navigation_type=NavigationType.STACK
    )
    manifest = RepoManifest(
        name="test-repo",
        github_url="https://github.com/test/repo",
        category=RepoCategory.PORTFOLIO
    )
    
    # Test case 1: Vulnerable dependency
    vulnerable_files = {
        "package.json": json.dumps({
            "dependencies": {
                "axios": "0.21.1", # Vulnerable (<1.6.0)
                "lodash": "4.17.15" # Vulnerable (<4.17.21)
            }
        })
    }
    
    engine = QualityGatesEngine(vulnerable_files, arch, manifest)
    engine._gate_security_sca()
    
    sca_gate = next(g for g in engine.gates if g.name == "security_sca")
    assert sca_gate.result == QualityGateResult.FAILED
    assert "axios" in sca_gate.details
    assert "lodash" in sca_gate.details

    # Test case 2: Safe dependencies
    safe_files = {
        "package.json": json.dumps({
            "dependencies": {
                "axios": "1.7.0",
                "react": "18.2.0"
            }
        })
    }
    
    engine_safe = QualityGatesEngine(safe_files, arch, manifest)
    engine_safe._gate_security_sca()
    sca_gate_safe = next(g for g in engine_safe.gates if g.name == "security_sca")
    assert sca_gate_safe.result == QualityGateResult.PASSED
