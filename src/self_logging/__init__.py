"""Logging setup for the application.

This module exports the routine `setup_logging`,
which can be called by the main program to configure Python's default logger.

Only the root logger is configured.
We assume only one logger but multiple handlers.
"""

import atexit
import logging
import logging.config
import logging.handlers
import sys
from pathlib import Path
from types import TracebackType

from .json import JSONFormatter

__all__ = ["setup_logging"]


def setup_logging(logging_dir: Path):
    """Setup logging for the application (main script).
    The main script should call this function first to properly setup logging.
    """

    if not logging_dir.is_dir():
        raise NotADirectoryError(f"{logging_dir} is not a directory.")

    logging.config.dictConfig(
        {
            # Mandatory to have a version, although we don't use multiple configurations for different purposes.
            "version": 1,
            # Allow third-party loggers to also log to the root logger.
            "disable_existing_loggers": False,
            # Define some formatters to be consumed by handlers.
            "formatters": {
                "stream": {
                    "format": "[%(levelname)s|%(module)s:%(lineno)d|%(asctime)s] %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
                "jsonl": {
                    # Set the formatter class
                    "()": JSONFormatter,
                },
            },
            # Define some handlers to be consumed by loggers.
            "handlers": {
                "stderr": {
                    # Use the "StreamHandler" class from the "logging" module.
                    "class": "logging.StreamHandler",
                    # Choose the "stream" formatter from the "formatters" section.
                    "formatter": "stream",
                    # Only log messages with level greater or equal than WARNING.
                    "level": "WARNING",
                    # Log to stderr.
                    "stream": "ext://sys.stderr",
                },
                "jsonl-file": {
                    # Use "RotatingFileHandler" to prevent having one very huge file.
                    "class": "logging.handlers.RotatingFileHandler",
                    # Choose the "jsonl" formatter from the "formatters" section.
                    "formatter": "jsonl",
                    # Log everything (level greater or equal than DEBUG).
                    "level": "DEBUG",
                    # Log to the file "logs.jsonl".
                    "filename": str(logging_dir / "logs.jsonl"),
                    # Log at most 1 MB of data per each file.
                    "maxBytes": 1024 * 1024,
                    # Keep at most 128 files
                    "backupCount": 128,
                },
                "@@QUEUE_HANDLER": {
                    # Use "QueueHandler" to allow logging without blocking the main thread.
                    "class": "logging.handlers.QueueHandler",
                    # Let the queue handler take over all other handlers.
                    "handlers": ["jsonl-file", "stderr"],
                    # Honor each destination handler's level.
                    "respect_handler_level": True,
                },
            },
            # Define the root logger. We only configure one logger.
            "root": {
                "handlers": ["@@QUEUE_HANDLER"],
                "level": "DEBUG",
            },
        }
    )

    # Start the queue handler and clean it when the program exits.
    queue_handler = logging.getHandlerByName("@@QUEUE_HANDLER")
    assert isinstance(queue_handler, logging.handlers.QueueHandler)  # enforce type
    assert queue_handler.listener is not None  # enforce type
    queue_handler.listener.start()
    atexit.register(queue_handler.listener.stop)

    # Log all raised warnings.
    logging.captureWarnings(True)

    # Log all raised exceptions.
    def custom_except_hook(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ):
        logger = logging.getLogger("__exception__")
        logger.critical(
            exc_value,
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = custom_except_hook
