"""
Structured Logging — JSON-formatted observability for the v3.0 pipeline.
Every log record includes correlation IDs (run_id, repo, stage) for searchable,
filterable log analysis across distributed pipeline runs.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from typing import Optional

# ── Correlation Context ────────────────────────────────────────────────────

_run_id: ContextVar[str] = ContextVar("run_id", default="")
_repo_name: ContextVar[str] = ContextVar("repo_name", default="")
_stage: ContextVar[str] = ContextVar("stage", default="")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_context(
    *,
    run_id: Optional[str] = None,
    repo_name: Optional[str] = None,
    stage: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> None:
    """Set correlation context for the current async task."""
    if run_id is not None:
        _run_id.set(run_id)
    if repo_name is not None:
        _repo_name.set(repo_name)
    if stage is not None:
        _stage.set(stage)
    if correlation_id is not None:
        _correlation_id.set(correlation_id)


def get_context() -> dict[str, str]:
    """Retrieve current correlation context."""
    return {
        "run_id": _run_id.get(""),
        "repo": _repo_name.get(""),
        "stage": _stage.get(""),
        "correlation_id": _correlation_id.get(""),
    }


def generate_correlation_id() -> str:
    """Generate a new correlation ID (UUID4 short form)."""
    from typing import cast
    return cast(str, uuid.uuid4().hex)[:12]


# ── Structured JSON Formatter ──────────────────────────────────────────────

class StructuredFormatter(logging.Formatter):
    """Outputs log records as single-line JSON objects.

    Each log line includes:
      - timestamp (ISO 8601)
      - level
      - logger name
      - message
      - run_id, repo, stage, correlation_id (from context vars)
      - exception info (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.") + f"{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject correlation context
        ctx = get_context()
        if ctx["run_id"]:
            entry["run_id"] = ctx["run_id"]
        if ctx["repo"]:
            entry["repo"] = ctx["repo"]
        if ctx["stage"]:
            entry["stage"] = ctx["stage"]
        if ctx["correlation_id"]:
            entry["correlation_id"] = ctx["correlation_id"]

        # Exception info
        if record.exc_info and record.exc_info[1]:
            from typing import cast, Tuple
            from types import TracebackType
            # Explicitly narrow expected type for formatException
            ei = cast(Tuple[type[BaseException], BaseException, Optional[TracebackType]], record.exc_info)
            entry["exception"] = self.formatException(ei)

        return json.dumps(entry, default=str)


# ── Human-Readable Formatter (fallback for local dev) ──────────────────────

class HumanFormatter(logging.Formatter):
    """Enhanced human-readable formatter with correlation context."""

    FORMAT = "%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s"

    def __init__(self):
        super().__init__(fmt=self.FORMAT, datefmt="%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_context()
        suffix_parts = []
        if ctx["run_id"]:
            suffix_parts.append(f"run={ctx['run_id']}")
        if ctx["repo"]:
            suffix_parts.append(f"repo={ctx['repo']}")
        if ctx["stage"]:
            suffix_parts.append(f"stage={ctx['stage']}")

        base = super().format(record)
        if suffix_parts:
            return f"{base} [{', '.join(suffix_parts)}]"
        return base


# ── Setup Function ─────────────────────────────────────────────────────────

def setup_structured_logging(
    *,
    verbose: bool = False,
    json_mode: bool = False,
) -> None:
    """Configure the root logger with structured or human-readable output.

    Args:
        verbose: Enable DEBUG level logging.
        json_mode: Output JSON-formatted logs (for production/CI).
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Remove existing handlers
    root = logging.getLogger()
    from typing import cast
    for handler in cast(list, root.handlers)[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler()

    if json_mode:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    root.setLevel(level)
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
