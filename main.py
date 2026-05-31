import importlib
import json
import os
import signal
import sys
import time
from typing import Optional

# ── path setup ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "helpers"))

import logger as log_mod
from logger import get_logger
import bridge_server
import rpc_client

log = get_logger("RPC")

# ── config ────────────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as _f:
    _cfg = json.load(_f)

CLIENT_ID        = _cfg["client_id"]
SCAN_INTERVAL    = float(_cfg.get("scan_interval", 3))
UPDATE_THROTTLE  = float(_cfg.get("update_throttle", 5))
BRIDGE_PORT      = int(_cfg.get("bridge_port", 7878))
SMALL_IMAGE      = _cfg.get("small_image", "online")
SMALL_TEXT       = _cfg.get("small_text", "🟢 Online")
DEFAULT_RPC      = _cfg.get("default_rpc", {})
PLUGIN_CFG       = _cfg.get("plugins", {})

# ── plugin loader ─────────────────────────────────────────────────────────────
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")


def load_plugins() -> list:
    plugins = []
    for filename in sorted(os.listdir(PLUGINS_DIR)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue
        module_name = filename[:-3]

        # Check enabled flag in config
        plugin_entry = PLUGIN_CFG.get(module_name, {})
        if isinstance(plugin_entry, dict) and not plugin_entry.get("enabled", True):
            log.info(f"Plugin '{module_name}' disabled in config — skipping")
            continue

        try:
            mod      = importlib.import_module(f"plugins.{module_name}")
            priority = getattr(mod, "PRIORITY", 99)
            plugins.append((priority, module_name, mod))
            log.info(f"Loaded plugin '{module_name}' (priority={priority})")
        except Exception as exc:
            log.error(f"Failed to load plugin '{module_name}': {exc}")

    plugins.sort(key=lambda x: x[0])
    return plugins


def get_active_plugin(plugins: list) -> tuple[Optional[str], Optional[object]]:
    for priority, name, mod in plugins:
        try:
            if mod.is_running():
                return name, mod
        except Exception as exc:
            log.warning(f"Plugin '{name}' is_running() raised: {exc}")
    return None, None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log.info("  NEON RPC v2  —  starting up")
    log.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── 1. Bridge server (VSCode extension) ──────────────────────────────
    srv = bridge_server.init(port=BRIDGE_PORT)

    # ── 2. FiveM pipe monitor ─────────────────────────────────────────────
    try:
        from plugins import fivem_bridge
        fivem_bridge.init_pipe_monitor(CLIENT_ID)
    except Exception as exc:
        log.warning(f"FiveM pipe monitor init failed: {exc}")

    # ── 3. Load plugins ───────────────────────────────────────────────────
    plugins = load_plugins()
    if not plugins:
        log.error("No plugins loaded — exiting")
        sys.exit(1)

    # ── 4. Connect Discord RPC ────────────────────────────────────────────
    client = rpc_client.RPCClient(CLIENT_ID, throttle=UPDATE_THROTTLE)
    if not client.connect():
        log.error("Could not connect to Discord — ensure Discord is running")
        log.info("Retrying in background via watchdog…")

    client.start_watchdog()

    # ── 5. Graceful shutdown handler ─────────────────────────────────────
    def _shutdown(sig, frame):
        log.info("Shutdown signal received — cleaning up…")
        client.clear()
        client.disconnect()
        client.stop_watchdog()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ── 6. Main loop ──────────────────────────────────────────────────────
    current_plugin: Optional[str] = None
    start_time = int(time.time())

    log.info("Entering main loop — press Ctrl+C to stop")

    while True:
        try:
            plugin_name, plugin_mod = get_active_plugin(plugins)

            if plugin_name:
                # Plugin switch → reset start time, force immediate update
                if plugin_name != current_plugin:
                    start_time    = int(time.time())
                    current_plugin = plugin_name
                    log.info(f"Active plugin: {plugin_name}")
                    client._last_update = 0.0   # bypass throttle for switch

                try:
                    rpc_data = plugin_mod.get_rpc()
                except Exception as exc:
                    log.error(f"Plugin '{plugin_name}' get_rpc() error: {exc}")
                    rpc_data = _default_rpc_data()

                client.update(
                    details     = rpc_data.get("details",     "NEON RPC v2"),
                    state       = rpc_data.get("state",       ""),
                    large_image = rpc_data.get("large_image", DEFAULT_RPC.get("image", "rpc_logo")),
                    large_text  = rpc_data.get("large_text",  "NEON RPC v2"),
                    small_image = SMALL_IMAGE,
                    small_text  = SMALL_TEXT,
                    start       = start_time,
                )

            time.sleep(SCAN_INTERVAL)

        except Exception as exc:
            log.error(f"Main loop exception: {exc}")
            time.sleep(5)


def _default_rpc_data() -> dict:
    return {
        "details":     DEFAULT_RPC.get("details", "💻 NEON RPC v2"),
        "state":       DEFAULT_RPC.get("state",   "⚡ Ready"),
        "large_image": DEFAULT_RPC.get("image",   "rpc_logo"),
        "large_text":  DEFAULT_RPC.get("large_text", "NEON RPC v2"),
    }


if __name__ == "__main__":
    main()
