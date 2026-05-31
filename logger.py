import logging
import sys
from datetime import datetime

# ── ANSI colour palette (cyber aesthetic) ──────────────────────────────────
_RESET  = "\033[0m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_DIM    = "\033[2m"
_BOLD   = "\033[1m"

_LEVEL_COLORS = {
    "INFO":    _GREEN,
    "WARNING": _YELLOW,
    "ERROR":   _RED,
}

_TAGS = {}   # registered module tags


class _NeonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts    = datetime.now().strftime("%H:%M:%S")
        tag   = getattr(record, "tag", record.name.upper())
        level = record.levelname
        color = _LEVEL_COLORS.get(level, _RESET)

        tag_str   = f"{_CYAN}[{tag}]{_RESET}"
        level_str = f"{color}{level:<7}{_RESET}"
        time_str  = f"{_DIM}{ts}{_RESET}"
        msg       = record.getMessage()

        return f"{time_str} {tag_str} {level_str} {msg}"


def _build_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_NeonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger


class TaggedLogger:
    """
    Usage:
        log = get_logger("VSCode")
        log.info("Editor update")
        log.warning("No workspace open")
        log.error("Bridge disconnected")
    """

    def __init__(self, tag: str):
        self._tag    = tag
        self._logger = _build_logger(f"neon.{tag.lower()}")

    def _extra(self) -> dict:
        return {"tag": self._tag}

    def info(self, msg: str):
        self._logger.info(msg, extra=self._extra())

    def warning(self, msg: str):
        self._logger.warning(msg, extra=self._extra())

    def error(self, msg: str):
        self._logger.error(msg, extra=self._extra())

    def debug(self, msg: str):
        self._logger.debug(msg, extra=self._extra())


def get_logger(tag: str) -> TaggedLogger:
    """Return (or reuse) a TaggedLogger for the given module tag."""
    if tag not in _TAGS:
        _TAGS[tag] = TaggedLogger(tag)
    return _TAGS[tag]


# ── module-level convenience ────────────────────────────────────────────────
rpc     = get_logger("RPC")
vscode  = get_logger("VSCode")
blender = get_logger("Blender")
fivem   = get_logger("FiveM")
bridge  = get_logger("Bridge")
system  = get_logger("System")
