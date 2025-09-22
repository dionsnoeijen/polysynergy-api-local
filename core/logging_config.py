import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
import os
import traceback


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs for CloudWatch"""

    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'path'):
            log_data["path"] = record.path
        if hasattr(record, 'method'):
            log_data["method"] = record.method
        if hasattr(record, 'status_code'):
            log_data["status_code"] = record.status_code
        if hasattr(record, 'duration'):
            log_data["duration"] = record.duration

        # Add custom fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for local development"""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(log_level: str = None, json_logs: bool = None):
    """Configure logging for the application"""

    # Get config from environment
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if json_logs is None:
        # Auto-detect: use JSON in Lambda, colored in local
        json_logs = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None or \
                   os.getenv("JSON_LOGS", "false").lower() == "true"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Set formatter based on environment
    if json_logs:
        formatter = StructuredFormatter()
    else:
        formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific logger levels to reduce noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with additional context methods"""
    logger = logging.getLogger(name)

    # Add convenience methods
    def log_with_context(level: int, msg: str, **kwargs):
        extra = {}
        if kwargs:
            extra['extra_fields'] = kwargs
        logger.log(level, msg, extra=extra)

    logger.debug_ctx = lambda msg, **kw: log_with_context(logging.DEBUG, msg, **kw)
    logger.info_ctx = lambda msg, **kw: log_with_context(logging.INFO, msg, **kw)
    logger.warning_ctx = lambda msg, **kw: log_with_context(logging.WARNING, msg, **kw)
    logger.error_ctx = lambda msg, **kw: log_with_context(logging.ERROR, msg, **kw)

    return logger


class LogContext:
    """Context manager for adding context to all logs within a block"""

    def __init__(self, **kwargs):
        self.context = kwargs
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()
        context = self.context

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)