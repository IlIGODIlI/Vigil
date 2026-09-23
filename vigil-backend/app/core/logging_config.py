import logging
import sys


def setup_logging() -> None:
    """Configures centralized logging for the application using Python's logging module.

    Log format: timestamp | log level | logger name | message
    Example: 2026-09-21 19:30:00 | INFO | vigil | Backend started
    """
    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("vigil")
