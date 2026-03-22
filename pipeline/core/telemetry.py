"""
Telemetry Engine — structured observability for the v3.0 pipeline.
Listens to the EventBus and logs agent decisions, stage transitions, and metrics.
Enhanced with Prometheus-compatible counters, histograms, and SLO tracking.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from pipeline.core.event_bus import event_bus, PipelineEvent

logger = logging.getLogger("pipeline.telemetry")


# ── Prometheus-Compatible Metrics Registry ─────────────────────────────────

@dataclass
class MetricsRegistry:
    """In-process metrics registry with Prometheus text format export.

    Tracks counters, gauges, and histogram-style distributions
    for pipeline observability without requiring a full Prometheus stack.
    """
    _counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _histograms: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def inc(self, name: str, amount: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += amount

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation (e.g., stage duration)."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Get current counter value."""
        return self._counters.get(self._make_key(name, labels), 0)

    def get_p95(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get the p95 value for a histogram metric."""
        values = self._histograms.get(self._make_key(name, labels), [])
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def get_avg(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get the average value for a histogram metric."""
        values = self._histograms.get(self._make_key(name, labels), [])
        return sum(values) / len(values) if values else 0.0

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text exposition format."""
        lines: list[str] = []

        # Export counters
        for key, value in sorted(self._counters.items()):
            name, label_str = self._parse_key(key)
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name}{label_str} {value}")

        # Export histogram summaries
        for key, values in sorted(self._histograms.items()):
            if not values:
                continue
            name, label_str = self._parse_key(key)
            sorted_vals = sorted(values)
            count = len(sorted_vals)
            total = sum(sorted_vals)
            p50_idx = int(count * 0.5)
            p95_idx = int(count * 0.95)
            p99_idx = int(count * 0.99)

            lines.append(f"# TYPE {name} summary")
            lines.append(f'{name}{{quantile="0.5"{label_str.strip("{}")}}} {sorted_vals[min(p50_idx, count-1)]:.3f}')
            lines.append(f'{name}{{quantile="0.95"{label_str.strip("{}")}}} {sorted_vals[min(p95_idx, count-1)]:.3f}')
            lines.append(f'{name}{{quantile="0.99"{label_str.strip("{}")}}} {sorted_vals[min(p99_idx, count-1)]:.3f}')
            lines.append(f"{name}_count{label_str} {count}")
            lines.append(f"{name}_sum{label_str} {total:.3f}")

        return "\n".join(lines) + "\n" if lines else ""

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._histograms.clear()

    @staticmethod
    def _make_key(name: str, labels: dict[str, str] | None = None) -> str:
        if not labels:
            return name
        label_parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_parts}}}"

    @staticmethod
    def _parse_key(key: str) -> tuple[str, str]:
        if "{" in key:
            name, rest = key.split("{", 1)
            return name, "{" + rest
        return key, ""


# Singleton metrics registry
metrics = MetricsRegistry()


# ── Telemetry Engine ───────────────────────────────────────────────────────

class TelemetryEngine:
    """Subscribes to pipeline events and provides structured observability."""

    def __init__(self):
        self.register_handlers()

    def register_handlers(self):
        """Register event handlers on the global event bus."""
        event_bus.subscribe(PipelineEvent.STAGE_STARTED, self.on_stage_started)
        event_bus.subscribe(PipelineEvent.STAGE_COMPLETED, self.on_stage_completed)
        event_bus.subscribe(PipelineEvent.STAGE_FAILED, self.on_stage_failed)
        event_bus.subscribe(PipelineEvent.ASSET_GENERATED, self.on_asset_generated)

    async def on_stage_started(self, data: dict):
        repo = data.get("repo", "unknown")
        stage = data.get("stage", "unknown")
        logger.info(f"🚀 [{repo}] Stage Started: {stage}")
        metrics.inc("pipeline_stages_started_total", labels={"stage": stage})

    async def on_stage_completed(self, data: dict):
        repo = data.get("repo", "unknown")
        stage = data.get("stage", "unknown")
        duration = data.get("duration_seconds", 0)
        logger.info(f"✅ [{repo}] Stage Completed: {stage}")
        metrics.inc("pipeline_stages_completed_total", labels={"stage": stage})
        if duration:
            metrics.observe("pipeline_stage_duration_seconds", float(duration), labels={"stage": stage})

    async def on_stage_failed(self, data: dict):
        repo = data.get("repo", "unknown")
        stage = data.get("stage", "unknown")
        error = data.get("error", "unknown error")
        logger.error(f"❌ [{repo}] Stage Failed: {stage} | Error: {error}")
        metrics.inc("pipeline_stages_failed_total", labels={"stage": stage})

    async def on_asset_generated(self, data: dict):
        repo = data.get("repo", "unknown")
        asset_type = data.get("type", "unknown")
        path = data.get("path", "unknown")
        logger.debug(f"📦 [{repo}] Asset Generated: {asset_type} at {path}")
        metrics.inc("pipeline_assets_generated_total", labels={"type": asset_type})

# Initialize telemetry engine (starts listening automatically)
telemetry = TelemetryEngine()
