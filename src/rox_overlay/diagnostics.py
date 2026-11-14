"""Local diagnostics: rotating log file and uncaught-exception capture."""

from __future__ import annotations

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from rox_overlay.config import app_data_dir

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(threadName)s %(name)s: %(message)s"


def default_log_path() -> Path:
    return app_data_dir() / "logs" / "overlay.log"


def configure_logging(path: Path | None = None, *, level: int = logging.INFO) -> Path:
    """Send application logs to a small rotating file (1 MB x 3) and log crashes."""
    log_path = path or default_log_path()
    root = logging.getLogger()
    root.setLevel(level)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    # A windowed PyInstaller build has no console: stderr may be None.
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(_LOG_FORMAT))
        console.setLevel(logging.WARNING)
        root.addHandler(console)
    _install_exception_hooks()
    return log_path


def _install_exception_hooks() -> None:
    logger = logging.getLogger("rox_overlay.crash")

    def excepthook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        logger.critical("exceção não tratada", exc_info=(exc_type, exc, tb))

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_value is not None:
            logger.critical(
                "exceção não tratada na thread %s",
                getattr(args.thread, "name", "?"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

    sys.excepthook = excepthook
    threading.excepthook = thread_hook
