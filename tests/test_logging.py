"""
Tests for src/core/logging_config.py

Covers: setup_logging, get_logger, StructuredFormatter.
"""

import logging
from src.core.logging_config import setup_logging, get_logger, StructuredFormatter


class TestSetupLogging:
    def test_sets_root_level(self):
        setup_logging("WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING
        # Reset
        setup_logging("INFO")

    def test_default_from_settings(self):
        setup_logging()
        root = logging.getLogger()
        # Default from settings is INFO
        assert root.level == logging.INFO

    def test_handler_added(self):
        setup_logging("INFO")
        root = logging.getLogger()
        assert len(root.handlers) >= 1


class TestGetLogger:
    def test_returns_logger(self):
        lg = get_logger("test_module")
        assert isinstance(lg, logging.Logger)
        assert lg.name == "test_module"


class TestStructuredFormatter:
    def test_format_basic_record(self):
        formatter = StructuredFormatter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        result = formatter.format(record)
        assert "hello" in result

    def test_format_with_extra_fields(self):
        formatter = StructuredFormatter(fmt="%(message)s")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        record.extra_fields = {"user_id": "u1", "channel": "slack"}
        result = formatter.format(record)
        assert "user_id=" in result
        assert "channel=" in result
