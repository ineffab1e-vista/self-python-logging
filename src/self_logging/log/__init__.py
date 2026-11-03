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

__all__ = ["JSONFormatter", "setup_logging"]

# logging modes:
# - log warnings, errors, and exceptions to stderr
# - log ordinary logs to local file
# - [TODO] log ordinary logs to remote server


def setup_logging(
    log_to_stderr: bool = True,
    log_to_dir: Path | None = None,
    log_to_server: None = None,
    capture_warnings: bool = False,
    capture_exceptions: bool = False,
):
    config = {
        # Mandatory to have a version, although we don't use multiple configurations for different purposes.
        "version": 1,
        # Allow third-party loggers to also log to the root logger.
        "disable_existing_loggers": False,
        # Define some formatters to be consumed by handlers.
        "formatters": {},
        # Define some handlers to be consumed by loggers.
        "handlers": {
            "@@QUEUE_HANDLER": {
                # Use "QueueHandler" to allow logging without blocking the main thread.
                "class": "logging.handlers.QueueHandler",
                # Let the queue handler take over all other handlers.
                "handlers": [],
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

    if log_to_stderr:
        config["formatters"]["stream"] = {
            "format": "%(asctime)s [%(levelname)8s]\n`%(module)s:%(lineno)d`\n%(message)s\n",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        }
        config["handlers"]["stderr"] = {
            # Use the "StreamHandler" class from the "logging" module.
            "class": "logging.StreamHandler",
            # Choose the "stream" formatter from the "formatters" section.
            "formatter": "stream",
            # Only log messages with level greater or equal than WARNING.
            "level": "WARNING",
            # Log to stderr.
            "stream": "ext://sys.stderr",
        }
        config["handlers"]["@@QUEUE_HANDLER"]["handlers"].append("stderr")

    if log_to_dir:
        config["formatters"]["jsonl"] = {
            # Set the formatter class
            "()": JSONFormatter,
        }
        config["handlers"]["local-file"] = {
            # Use "RotatingFileHandler" to prevent having one very huge file.
            "class": "logging.handlers.RotatingFileHandler",
            # Choose the "jsonl" formatter from the "formatters" section.
            "formatter": "jsonl",
            # Log everything (level greater or equal than DEBUG).
            "level": "DEBUG",
            # Log to the file "logs.jsonl".
            "filename": str(log_to_dir / "logs.jsonl"),
            # Log at most 1 MB of data per each file.
            "maxBytes": 1024 * 1024,
            # Keep at most 128 files
            "backupCount": 128,
        }
        config["handlers"]["@@QUEUE_HANDLER"]["handlers"].append("local-file")

    if log_to_server:
        config["handlers"]["server"] = {
            "class": "logging.handlers.HTTPHandler",
            "level": "DEBUG",
            "host": "localhost:8443",  # [TODO] parameter
            "url": "/logs",  # [TODO] parameter
            "method": "POST",
            "secure": True,  # [TODO] parameter
            "context": context,  # [TODO] parameter
        }
        config["handlers"]["@@QUEUE_HANDLER"]["handlers"].append("server")

    # pass the modified config and give it to all
    logging.config.dictConfig(config)

    # Start the queue handler and clean it when the program exits.
    queue_handler = logging.getHandlerByName("@@QUEUE_HANDLER")
    assert isinstance(queue_handler, logging.handlers.QueueHandler)  # enforce type
    assert queue_handler.listener is not None  # enforce type
    queue_handler.listener.start()
    atexit.register(queue_handler.listener.stop)

    if capture_warnings:
        # Log all raised warnings.
        logging.captureWarnings(True)

    if capture_exceptions:
        # Log all raised exceptions.
        def custom_except_hook(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_traceback: TracebackType | None,
        ):
            logger = logging.getLogger("root")
            logger.critical(
                exc_value,
                exc_info=(exc_type, exc_value, exc_traceback),
            )
            sys.__excepthook__(exc_type, exc_value, exc_traceback)

        sys.excepthook = custom_except_hook
