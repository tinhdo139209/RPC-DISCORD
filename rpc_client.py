
import threading
import time
from typing import Optional

from pypresence import Presence, InvalidPipe, InvalidID

from logger import get_logger

log = get_logger("RPC")

_PIPE_RANGE    = range(0, 10)
_RECONNECT_DELAY = 10     # seconds between reconnect attempts
_HEARTBEAT_INTERVAL = 30  # seconds


class RPCClient:
    def __init__(self, client_id: str, throttle: float = 5.0):
        self._client_id  = client_id
        self._throttle   = throttle
        self._rpc: Optional[Presence] = None
        self._connected  = False
        self._lock       = threading.Lock()
        self._last_update = 0.0
        self._last_payload: Optional[dict] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._running = False

    # ── connection ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """
        Try every pipe index until connection succeeds.
        Returns True on success.
        """
        for pipe in _PIPE_RANGE:
            try:
                rpc = Presence(self._client_id, pipe=pipe)
                rpc.connect()
                with self._lock:
                    self._rpc       = rpc
                    self._connected = True
                log.info(f"Connected to Discord (pipe={pipe})")
                return True
            except (InvalidPipe, FileNotFoundError):
                continue
            except InvalidID:
                log.error(f"Invalid client_id: {self._client_id}")
                return False
            except Exception as exc:
                log.warning(f"Pipe {pipe} failed: {exc}")
                continue

        log.error("Could not connect to Discord on any pipe — is Discord running?")
        return False

    def disconnect(self):
        with self._lock:
            if self._rpc and self._connected:
                try:
                    self._rpc.close()
                except Exception:
                    pass
                self._connected = False
                self._rpc       = None
        log.info("Disconnected from Discord RPC")

    @property
    def connected(self) -> bool:
        return self._connected

    # ── update ────────────────────────────────────────────────────────────

    def update(self, **kwargs) -> bool:
        """
        Send a presence update.
        Throttled: skips if called faster than self._throttle seconds.
        Returns True if update was actually sent.
        """
        now = time.monotonic()
        if now - self._last_update < self._throttle:
            return False

        with self._lock:
            if not self._connected or not self._rpc:
                return False
            try:
                self._rpc.update(**kwargs)
                self._last_update  = now
                self._last_payload = kwargs
                return True
            except (BrokenPipeError, ConnectionResetError, InvalidPipe):
                log.warning("Discord pipe lost — scheduling reconnect")
                self._connected = False
                return False
            except Exception as exc:
                log.error(f"RPC update error: {exc}")
                self._connected = False
                return False

    def force_update(self, **kwargs) -> bool:
        """Bypass throttle for state-change events (new plugin activated)."""
        self._last_update = 0.0
        return self.update(**kwargs)

    def clear(self):
        """Clear the presence (shows nothing in Discord)."""
        with self._lock:
            if self._connected and self._rpc:
                try:
                    self._rpc.clear()
                except Exception:
                    pass

    # ── watchdog ──────────────────────────────────────────────────────────

    def start_watchdog(self):
        """Daemon thread: reconnect whenever Discord connection drops."""
        self._running = True
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, daemon=True
        )
        self._watchdog_thread.start()
        log.info("Watchdog started")

    def stop_watchdog(self):
        self._running = False

    def _watchdog_loop(self):
        last_heartbeat = time.monotonic()

        while self._running:
            time.sleep(2)

            # ── reconnect if dropped ──────────────────────────────────────
            if not self._connected:
                log.info(f"Reconnecting in {_RECONNECT_DELAY} s…")
                time.sleep(_RECONNECT_DELAY)
                if self.connect() and self._last_payload:
                    # Restore last known presence after reconnect
                    self.force_update(**self._last_payload)

            # ── heartbeat ────────────────────────────────────────────────
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                last_heartbeat = now
                if self._connected:
                    log.debug("Heartbeat OK")
                else:
                    log.warning("Heartbeat — Discord not connected")

    # ── context manager ───────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        self.start_watchdog()
        return self

    def __exit__(self, *_):
        self.stop_watchdog()
        self.clear()
        self.disconnect()
