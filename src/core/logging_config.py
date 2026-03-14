"""
Logging configuration for the Agno Memory Bridge API.

Sets up structured logging with proper formatting, level control,
and error tracking for production environments.
"""

import logging
import sys
from typing import Optional

from src.core.config import settings


class StructuredFormatter(logging.Formatter):
    """
    Structured logging formatter that adds context to logs.
    
    Outputs logs in a semi-structured format:
    [LEVEL] [timestamp] [logger_name] message {extra_data}
    
    Suitable for both local development and cloud logging services.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with structure."""
        
        msg = super().format(record)

        if hasattr(record, "extra_fields"):
            extra_str = " ".join(
                f"{k}={v!r}" for k, v in record.extra_fields.items()
            )
            if extra_str:
                msg = f"{msg} {{{extra_str}}}"

        return msg


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure application logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to settings.log_level if not provided.
    """
    log_level = level or settings.log_level

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="[%(levelname)s] %(asctime)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("agno").setLevel(logging.INFO)

    logging.info(f"Logging configured: level={log_level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
