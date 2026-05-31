"""
NEON RPC v2 — helpers/discord_pipe_reader.py

Reads Discord's local IPC pipe to extract Rich Presence data broadcast
by other applications (e.g. FiveM servers).  Used for RPC mirroring.

Discord IPC lives at:
  Windows : \\.\pipe\discord-ipc-{0..9}
  Linux   : $XDG_RUNTIME_DIR/discord-ipc-{0..9}  (or /tmp/…)
  macOS   : $TMPDIR/discord-ipc-{0..9}

We listen passively — we never inject data; we only parse what Discord
already exposes to this process's local pipe socket.
"""

import json
import os
import struct
import sys
import threading
import time
from typing import Optional

from logger import get_logger

log = get_logger("PipeReader")

# ── Path resolution ──────────────────────────────────────────────────────────

def _pipe_paths() -> list[str]:
    paths = []
    if sys.platform == "win32":
        for i in range(10):
            paths.append(f"\\\\.\\pipe\\discord-ipc-{i}")
    else:
        base = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or "/tmp"
        for i in range(10):
            paths.append(os.path.join(base, f"discord-ipc-{i}"))
    return paths


# ── Low-level frame parser ───────────────────────────────────────────────────

def _read_frame(handle) -> Optional[dict]:
    """
    Read one Discord IPC frame.
    Frame format: [op: uint32 LE][length: uint32 LE][payload: bytes]
    """
    try:
        header = handle.read(8)
        if len(header) < 8:
            return None
        _op, length = struct.unpack("<II", header)
        payload     = handle.read(length)
        if len(payload) < length:
            return None
        return json.loads(payload.decode("utf-8", errors="ignore"))
    except Exception:
        return None


# ── Presence extractor ───────────────────────────────────────────────────────

def _extract_presence(frame: dict) -> Optional[dict]:
    """
    Pull details / state / assets from a Discord ACTIVITY_UPDATE frame.
    Returns None when the frame is not an activity event.
    """
    try:
        evt  = frame.get("evt")
        data = frame.get("data", {})

        if evt not in ("ACTIVITY_UPDATE", "ACTIVITY_JOIN", None):
            return None

        activity = data.get("activity") or data
        if not activity:
            return None

        assets = activity.get("assets", {})
        return {
            "details":     activity.get("details", ""),
            "state":       activity.get("state", ""),
            "large_image": assets.get("large_image", ""),
            "large_text":  assets.get("large_text", ""),
            "small_image": assets.get("small_image", ""),
            "app_id":      str(activity.get("application_id", "")),
            "name":        activity.get("name", ""),
        }
    except Exception:
        return None


# ── Background monitor ───────────────────────────────────────────────────────

class DiscordPipeMonitor:
    """
    Runs a daemon thread that continuously reads Discord's IPC pipe and
    caches the most-recent Rich Presence payload seen from any application
    other than ourselves (identified by client_id).

    Usage:
        monitor = DiscordPipeMonitor(own_client_id="123456")
        monitor.start()
        ...
        presence = monitor.get_latest()   # returns dict or None
    """

    def __init__(self, own_client_id: str = ""):
        self._own_id  = str(own_client_id)
        self._latest: Optional[dict] = None
        self._lock    = threading.Lock()
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        log.info("Discord pipe monitor started")

    def stop(self):
        self._running = False

    def get_latest(self) -> Optional[dict]:
        with self._lock:
            return self._latest.copy() if self._latest else None

    # ── internal ──────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            connected = False
            for path in _pipe_paths():
                try:
                    if sys.platform == "win32":
                        handle = open(path, "r+b", buffering=0)
                    else:
                        if not os.path.exists(path):
                            continue
                        import socket
                        sock = socket.socket(socket.AF_UNIX)
                        sock.connect(path)
                        handle = sock.makefile("rb")

                    log.info(f"Monitoring Discord pipe: {path}")
                    connected = True

                    while self._running:
                        frame = _read_frame(handle)
                        if frame is None:
                            break
                        presence = _extract_presence(frame)
                        if presence and presence.get("app_id") != self._own_id:
                            with self._lock:
                                self._latest = presence

                    handle.close()
                    break

                except FileNotFoundError:
                    continue
                except Exception as exc:
                    log.warning(f"Pipe read error on {path}: {exc}")
                    continue

            if not connected:
                log.debug("No Discord pipe found — retrying in 15 s")

            time.sleep(15)
