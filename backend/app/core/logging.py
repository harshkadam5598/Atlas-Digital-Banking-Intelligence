"""
Atlas – Digital Banking Intelligence Platform
Structured Logging Configuration

Configures Loguru with structured output for both development
(human-readable) and production (JSON) environments.
"""

import sys
from pathlib import Path

from loguru import logger

from backend.app.core.config import settings

# Ensure log directory exists
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def configure_logging() -> None:
    """
    Set up Atlas structured logging.
    - Development: colorized console output with full context
    - Production: JSON structured logs to file + console
    """
    logger.remove()  # Remove default handler

    log_format_dev = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    log_format_prod = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )

    if settings.is_development:
        logger.add(
            sys.stdout,
            format=log_format_dev,
            level=settings.log_level,
            colorize=True,
        )
    else:
        # Console (structured, no color)
        logger.add(
            sys.stdout,
            format=log_format_prod,
            level=settings.log_level,
            colorize=False,
            serialize=True,  # JSON output in production
        )

    # Always write to rotating file
    logger.add(
        LOG_DIR / "atlas_{time:YYYY-MM-DD}.log",
        format=log_format_prod,
        level="DEBUG",
        rotation="00:00",     # New file each day
        retention="30 days",  # Keep 30 days of logs
        compression="gz",
        enqueue=True,         # Thread-safe async logging
    )

    # Separate error log
    logger.add(
        LOG_DIR / "atlas_errors.log",
        format=log_format_prod,
        level="ERROR",
        rotation="100 MB",
        retention="90 days",
        compression="gz",
        enqueue=True,
    )

    logger.info(f"Atlas logging initialized | env={settings.env} | level={settings.log_level}")
