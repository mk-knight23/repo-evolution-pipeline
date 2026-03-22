import pytest
from pipeline.core.models import RepoEvolutionState, PipelineStage
from pipeline.core.stages import StageRegistry, BaseStage, FunctionalStage

class MockStage(BaseStage):
    async def run(self, state: RepoEvolutionState) -> RepoEvolutionState:
        state.warnings.append(f"Ran {self.name.value}")
        return state

@pytest.mark.asyncio
async def test_stage_registry():
    registry = StageRegistry()
    
    stage1 = MockStage(PipelineStage.CLONING)
    stage2 = MockStage(PipelineStage.ANALYZING)
    
    registry.register(stage1)
    registry.register(stage2)
    
    assert registry.get(PipelineStage.CLONING) == stage1
    assert registry.get(PipelineStage.ANALYZING) == stage2
    
    seq = registry.get_sequence()
    assert len(seq) == 2
    assert seq[0] == stage1
    assert seq[1] == stage2

@pytest.mark.asyncio
async def test_functional_stage():
    state = RepoEvolutionState(repo_name="test", github_url="test")
    
    async def mock_func(s: RepoEvolutionState):
        s.warnings.append("func_ran")
        return s
        
    stage = FunctionalStage(PipelineStage.CLONING, mock_func)
    await stage.run(state)
    
    assert "func_ran" in state.warnings

@pytest.mark.asyncio
async def test_registry_sequence_filtering():
    registry = StageRegistry()
    registry.register(MockStage(PipelineStage.CLONING))
    registry.register(MockStage(PipelineStage.ANALYZING))
    registry.register(MockStage(PipelineStage.ARCHITECTING))
    
    enabled = [PipelineStage.CLONING, PipelineStage.ARCHITECTING]
    seq = registry.get_sequence(enabled_stages=enabled)
    
    assert len(seq) == 2
    assert seq[0].name == PipelineStage.CLONING
    assert seq[1].name == PipelineStage.ARCHITECTING
