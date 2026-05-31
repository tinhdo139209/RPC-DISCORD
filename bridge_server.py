import asyncio
import json
import threading
from typing import Optional

try:
    import websockets
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False

from logger import get_logger

log = get_logger("Bridge")

_DEFAULT_PORT = 7878


class BridgeServer:
    """
    Runs an asyncio WebSocket server in a daemon thread.
    Thread-safe access to the latest VSCode state via .get_state().
    """

    def __init__(self, port: int = _DEFAULT_PORT):
        self._port    = port
        self._state: Optional[dict] = None
        self._lock    = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._loop:   Optional[asyncio.AbstractEventLoop] = None

    # ── public API ────────────────────────────────────────────────────────

    def start(self):
        if not _WS_AVAILABLE:
            log.warning("websockets not installed — bridge server disabled. "
                        "Run: pip install websockets")
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info(f"Bridge server listening on ws://localhost:{self._port}")

    def get_state(self) -> Optional[dict]:
        with self._lock:
            return self._state.copy() if self._state else None

    def is_connected(self) -> bool:
        with self._lock:
            return self._state is not None

    # ── internal ──────────────────────────────────────────────────────────

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as exc:
            log.error(f"Bridge server crashed: {exc}")

    async def _serve(self):
        async def handler(ws):
            remote = ws.remote_address
            log.info(f"VSCode extension connected from {remote}")
            try:
                async for raw in ws:
                    try:
                        payload = json.loads(raw)
                        with self._lock:
                            self._state = payload
                        log.info(
                            f"Editor update — "
                            f"{payload.get('file', '?')} "
                            f"L{payload.get('line', '?')} "
                            f"❌{payload.get('errors', 0)} "
                            f"⚠{payload.get('warnings', 0)}"
                        )
                    except json.JSONDecodeError as exc:
                        log.warning(f"Bad JSON from extension: {exc}")
            except Exception as exc:
                log.warning(f"Extension disconnected: {exc}")
            finally:
                with self._lock:
                    self._state = None
                log.info("VSCode extension disconnected — state cleared")

        async with websockets.serve(handler, "localhost", self._port):
            await asyncio.Future()   # run forever


# ── module-level singleton ───────────────────────────────────────────────────
_server: Optional[BridgeServer] = None


def init(port: int = _DEFAULT_PORT) -> BridgeServer:
    global _server
    _server = BridgeServer(port)
    _server.start()
    return _server


def get_server() -> Optional[BridgeServer]:
    return _server
