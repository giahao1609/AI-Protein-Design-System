"""Structured logging setup.

Uses structlog for JSON-formatted, contextual logging.
Every log entry includes structured fields for filtering and analysis.

Example output:
{
  "run_id": "run_abc123",
  "target_id": "tgt_xyz",
  "candidate_id": "cand_001",
  "stage": "structure_prediction",
  "model": "dummy",
  "status": "success",
  "event": "prediction_complete",
  "timestamp": "2026-01-01T00:00:00Z"
}
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, cast

import structlog


def setup_logging(
    level: str = "INFO",
    log_format: str = "console",
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_format: Output format ('json' or 'console').
        log_file: Optional file path for log output.
    """
    # Determine from environment if not explicitly set
    level = os.environ.get("PROTEIN_DESIGN_LOG_LEVEL", level).upper()
    log_format = os.environ.get("PROTEIN_DESIGN_LOG_FORMAT", log_format).lower()

    # Choose renderer
    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(
            file=open(log_file, "a", encoding="utf-8") if log_file else sys.stderr
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(**initial_context: Any) -> structlog.BoundLogger:
    """Get a structured logger with optional initial context.

    Usage:
        log = get_logger(run_id="run_abc", target_id="tgt_xyz")
        log.info("generation_started", generator="dummy", num_candidates=10)
    """
    return cast(structlog.BoundLogger, structlog.get_logger(**initial_context))
