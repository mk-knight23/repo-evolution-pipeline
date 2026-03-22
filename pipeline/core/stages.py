"""
Pipeline Stages — extensible stage registry for the evolution pipeline.
Allows modularizing transformation steps and enabling/disabling them via config.
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Callable, Optional

from pipeline.core.models import RepoEvolutionState, PipelineStage

logger = logging.getLogger("pipeline.stages")


class BaseStage(abc.ABC):
    """
    Base interface for a pipeline stage.
    Each stage takes the current state and returns an updated state.
    """

    def __init__(self, name: PipelineStage, description: str = ""):
        self.name = name
        self.description = description or name.value.replace("_", " ").title()

    @abc.abstractmethod
    async def run(self, state: RepoEvolutionState) -> RepoEvolutionState:
        """Execute the stage logic."""
        pass


class FunctionalStage(BaseStage):
    """A stage implemented as a simple async function."""

    def __init__(
        self,
        name: PipelineStage,
        func: Callable[[RepoEvolutionState], Any],
        description: str = "",
    ):
        super().__init__(name, description)
        self.func = func

    async def run(self, state: RepoEvolutionState) -> RepoEvolutionState:
        result = await self.func(state)
        if isinstance(result, RepoEvolutionState):
            return result
        return state


class StageRegistry:
    """Central registry for all available pipeline stages."""

    def __init__(self):
        self._stages: dict[PipelineStage, BaseStage] = {}
        self._sequence: list[PipelineStage] = []

    def register(self, stage: BaseStage, index: Optional[int] = None):
        """Register a stage in the registry."""
        self._stages[stage.name] = stage
        if stage.name not in self._sequence:
            if index is not None:
                self._sequence.insert(index, stage.name)
            else:
                self._sequence.append(stage.name)
        logger.debug(f"Registered stage: {stage.name} ({stage.description})")

    def get(self, name: PipelineStage) -> Optional[BaseStage]:
        """Retrieve a stage by name."""
        return self._stages.get(name)

    def get_sequence(self, enabled_stages: Optional[list[PipelineStage]] = None) -> list[BaseStage]:
        """
        Get the ordered list of enabled stages.
        If enabled_stages is None, returns all registered stages in order.
        """
        seq = []
        target_list = enabled_stages if enabled_stages is not None else self._sequence
        
        for name in target_list:
            stage = self._stages.get(name)
            if stage:
                seq.append(stage)
        return seq

    def remove(self, name: PipelineStage):
        """Remove a stage from the registry."""
        self._stages.pop(name, None)
        if name in self._sequence:
            self._sequence.remove(name)


# Global registry instance
registry = StageRegistry()
