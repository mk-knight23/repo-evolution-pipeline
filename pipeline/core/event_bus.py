"""
Event Bus — central message broker for the v3.0 pipeline.
Enables asynchronous communication between agents and decoupling of stages.
Enhanced with typed event data, event history, and correlation ID propagation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class EventData:
    """Typed event payload with correlation context."""
    event_type: str
    timestamp: float = field(default_factory=time.time)
    run_id: str = ""
    correlation_id: str = ""
    repo: str = ""
    stage: str = ""
    payload: dict = field(default_factory=dict)


class EventBus:
    """Asynchronous event bus with typed events, history buffer, and correlation support."""

    MAX_HISTORY = 1000

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], Coroutine[Any, Any, None]]]] = defaultdict(list)
        self._history: deque[EventData] = deque(maxlen=self.MAX_HISTORY)
        self.logger = logging.getLogger("pipeline.event_bus")

    def subscribe(self, event_type: str, handler: Callable[[Any], Coroutine[Any, Any, None]]):
        """Subscribe a handler to an event type."""
        self._subscribers[event_type].append(handler)
        self.logger.debug(f"Subscribed {handler.__name__} to {event_type}")

    async def emit(self, event_type: str, data: Any):
        """Emit an event to all subscribers and record it in history."""
        # Build typed event for history
        event = EventData(
            event_type=event_type,
            run_id=data.get("run_id", "") if isinstance(data, dict) else "",
            correlation_id=data.get("correlation_id", "") if isinstance(data, dict) else "",
            repo=data.get("repo", "") if isinstance(data, dict) else "",
            stage=data.get("stage", "") if isinstance(data, dict) else "",
            payload=data if isinstance(data, dict) else {"raw": str(data)},
        )
        self._history.append(event)

        self.logger.debug(f"Emitting {event_type} with data: {type(data).__name__}")
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return

        # Execute all handlers concurrently
        await asyncio.gather(*[handler(data) for handler in handlers], return_exceptions=True)

    def get_history(
        self,
        event_type: Optional[str] = None,
        run_id: Optional[str] = None,
        repo: Optional[str] = None,
        limit: int = 100,
    ) -> list[EventData]:
        """Retrieve event history, optionally filtered by type or repo."""
        events = list(self._history)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if run_id:
            events = [e for e in events if e.run_id == run_id]
        if repo:
            events = [e for e in events if e.repo == repo]
        from typing import cast
        return cast(list, events)[-limit:]

    def clear(self):
        """Clear event history and all subscribers."""
        self._history.clear()
        self._subscribers.clear()

    @property
    def event_count(self) -> int:
        """Total events in history."""
        return len(self._history)


class PipelineEvent:
    """Event type constants for the pipeline."""
    STAGE_STARTED = "stage.started"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    ASSET_GENERATED = "asset.generated"
    METRIC_UPDATED = "metric.updated"
    CIRCUIT_BREAKER_TRIPPED = "circuit_breaker.tripped"
    QUALITY_GATE_RESULT = "quality_gate.result"

# Global event bus instance
event_bus = EventBus()
