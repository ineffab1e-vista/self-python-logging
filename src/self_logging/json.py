import json
import logging
from datetime import UTC
from datetime import datetime as dt
from typing import override

LOG_RECORD_BUILTIN_ATTRS = frozenset(
    [
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    ]
)
"""Attributes that are built-in to the log record and should not be included in the "extra" field.

Borrowed from mCoding. 
See https://github.com/mCodingLLC/VideosSampleCode/blob/e77d95c61514e591a250a6fd91d048024c1f479d/videos/135_modern_logging/mylogger.py#L6C1-L30C2
"""


class JSONFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "loggerName": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "timestamp": dt.fromtimestamp(record.created, tz=UTC).isoformat(),
            "module": record.module,
            "file": f"{record.filename}:{record.lineno}",
            "process": f"{record.processName}:{record.process}",
            "thread": f"{record.threadName}:{record.thread}",
            "exception": record.exc_info,
            "stack": record.stack_info,
            "extra": {
                k: v
                for k, v in record.__dict__.items()
                if k not in LOG_RECORD_BUILTIN_ATTRS
            },
        }

        return json.dumps({k: v for k, v in log_dict.items() if v})
