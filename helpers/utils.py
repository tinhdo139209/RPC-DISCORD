"""
NEON RPC v2 — helpers/utils.py
Shared utilities: process detection, path sanitisation, throttle guard.
"""

import os
import time
from typing import Optional

import psutil


def is_process_running(names: list[str]) -> tuple[bool, Optional[str]]:
    """
    Check whether any process whose name contains one of `names` is running.
    Returns (found: bool, matched_name: str | None).
    Case-insensitive match.
    """
    names_lower = [n.lower() for n in names]
    try:
        for proc in psutil.process_iter(["name"]):
            proc_name = (proc.info.get("name") or "").lower()
            for target in names_lower:
                if target in proc_name:
                    return True, proc.info["name"]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return False, None


def get_process_cmdline(names: list[str]) -> Optional[str]:
    """Return the full command-line string of the first matching process."""
    names_lower = [n.lower() for n in names]
    try:
        for proc in psutil.process_iter(["name", "cmdline"]):
            proc_name = (proc.info.get("name") or "").lower()
            for target in names_lower:
                if target in proc_name:
                    cmdline = proc.info.get("cmdline") or []
                    return " ".join(cmdline)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return None


def sanitise_path(path: str) -> str:
    """
    Strip the full filesystem path for privacy.
    Returns only the final folder + filename: workspace/file.py
    """
    if not path:
        return ""
    parts = path.replace("\\", "/").split("/")
    # Return last two segments (parent folder + filename)
    if len(parts) >= 2:
        return "/".join(parts[-2:])
    return parts[-1] if parts else ""


def truncate(text: str, max_len: int = 128) -> str:
    """Truncate a string to fit Discord RPC field limits."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


class Throttle:
    """
    Rate-limit a callable: only allow execution every `interval` seconds.

    Usage:
        t = Throttle(5)
        if t.ready():
            rpc.update(...)
    """

    def __init__(self, interval: float):
        self._interval = interval
        self._last     = 0.0

    def ready(self) -> bool:
        now = time.monotonic()
        if now - self._last >= self._interval:
            self._last = now
            return True
        return False

    def force_reset(self):
        """Force the next call to pass."""
        self._last = 0.0
