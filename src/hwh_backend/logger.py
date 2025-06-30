import logging
from enum import StrEnum
from typing import Optional

logger = logging.getLogger("hwh_backend")


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"


def _parse_log_level(level: str) -> int:
    """Parse verbosity level from config settings.
    During pip install/build, verbosity is passed via --config-setting verbose="debug"
    """
    match level.lower():
        case "debug": return logging.DEBUG
        case "info": return logging.INFO
        case "warning": return logging.WARNING
        case _: raise ValueError("log level must be one of {debug, info, warning}")


def setup_logging(config_settings: Optional[dict[str, str]] = None):
    """Configure logging based on config settings."""
    log_level = (_parse_log_level(config_settings.get("verbose", "warning"))
                 if config_settings else logging.WARNING)

    logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    below_warning = logging.StreamHandler()
    below_warning.setLevel(logging.DEBUG)
    below_warning.addFilter(lambda m: m.levelno < logging.WARNING)
    warning_and_above = logging.StreamHandler()
    warning_and_above.setLevel(logging.WARNING)

    # Format to match pip's output style
    warning_and_above.setFormatter(logging.Formatter("  hwh-backend: %(message)s"))
    below_warning.setFormatter(logging.Formatter("%(levelname)s: hwh-backend: %(message)s"))

    logger.addHandler(below_warning)
    logger.addHandler(warning_and_above)

    # Log initial setup
    logger.debug(f"Backend logging initialized (verbosity={log_level})")
