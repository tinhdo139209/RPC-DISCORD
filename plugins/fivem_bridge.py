
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "helpers"))

import re
from typing import Optional

from utils import is_process_running, get_process_cmdline, truncate
from asset_mapper import resolve_server_asset
from discord_pipe_reader import DiscordPipeMonitor
from logger import get_logger

log = get_logger("FiveM")

PRIORITY = 1

_FIVEM_NAMES = ["fivem", "fivem.exe", "citizenfx", "gta5.exe"]

# Shared monitor instance (started once by main.py)
_pipe_monitor: Optional[DiscordPipeMonitor] = None


def init_pipe_monitor(own_client_id: str):
    """Called by main.py at startup to begin pipe monitoring."""
    global _pipe_monitor
    _pipe_monitor = DiscordPipeMonitor(own_client_id=own_client_id)
    _pipe_monitor.start()


def is_running() -> bool:
    found, name = is_process_running(_FIVEM_NAMES)
    if found:
        log.info(f"Detected: {name}")
    return found


def get_rpc() -> dict:
    # ── Layer 2: try pipe mirror first ───────────────────────────────────
    mirrored = _try_mirror()
    if mirrored:
        return mirrored

    # ── Layer 1 fallback: generic FiveM presence ─────────────────────────
    server_name = _detect_server_name()
    if server_name:
        asset = resolve_server_asset(server_name)
        log.info(f"Server: {server_name} → asset: {asset}")
        return {
            "details":     truncate(f"🎮 {server_name}", 128),
            "state":       "🚓 Đang Roleplay",
            "large_image": asset,
            "large_text":  f"FIVEM — {server_name.upper()}",
        }

    # ── Generic FiveM (no server info) ───────────────────────────────────
    log.info("FiveM running — no server info available")
    return {
        "details":     "🎮 FiveM",
        "state":       "🌆 Đang chơi GTA V",
        "large_image": "fivem_logo",
        "large_text":  "FIVEM",
    }


# ── Layer 2: Discord pipe mirror ─────────────────────────────────────────────

def _try_mirror() -> Optional[dict]:
    if _pipe_monitor is None:
        return None

    presence = _pipe_monitor.get_latest()
    if not presence:
        return None

    # Only mirror if this looks like a FiveM / GTA presence
    name = presence.get("name", "").lower()
    if not any(k in name for k in ["fivem", "gta", "cfx", "rage", "five"]):
        return None

    server_name = presence.get("details") or presence.get("name") or "FiveM"
    state_text  = presence.get("state") or "🚓 Đang Roleplay"

    # Layer 3: resolve asset
    large_image = presence.get("large_image") or resolve_server_asset(server_name)
    large_text  = presence.get("large_text") or f"FIVEM — {server_name.upper()}"

    log.info(f"Mirrored RPC from '{server_name}'")

    return {
        "details":     truncate(f"🎮 {server_name}", 128),
        "state":       truncate(state_text, 128),
        "large_image": large_image,
        "large_text":  truncate(large_text, 128),
    }


# ── Layer 1: server name from process ────────────────────────────────────────

def _detect_server_name() -> str:
    """
    Attempt to read the connected server name from FiveM's command line.
    FiveM passes the server connect address as an argument in some launchers.
    """
    cmdline = get_process_cmdline(_FIVEM_NAMES) or ""

    # Look for +connect <ip>:<port> or server name hints
    match = re.search(r'\+connect\s+([\w.\-:]+)', cmdline, re.IGNORECASE)
    if match:
        return match.group(1)

    return ""
