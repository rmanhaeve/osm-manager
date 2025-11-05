from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from .config import settings


def setup_logging() -> None:
    """Configure structlog and standard logging for JSON output."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        timestamper,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    log_level_value = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level_value),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
