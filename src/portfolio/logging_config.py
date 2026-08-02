"""Process-wide logging setup for batch and API entrypoints."""

from __future__ import annotations

import logging
import os

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str | int | None = None) -> None:
    """Configure root logging once for CLI/batch/API processes.

    Level comes from ``level``, else ``PORTFOLIO_LOG_LEVEL``, else INFO.
    """
    if isinstance(level, int):
        resolved_level: int = level
    else:
        name = (level or os.getenv("PORTFOLIO_LOG_LEVEL") or "INFO").upper()
        resolved_level = getattr(logging, name, logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
        force=True,
    )
