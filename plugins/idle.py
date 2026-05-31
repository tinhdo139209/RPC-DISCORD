PRIORITY = 99


def is_running() -> bool:
    return True   # always active as fallback


def get_rpc() -> dict:
    return {
        "details":     "💻 Không edit file",
        "state":       "🧋 Đang Uống Bạc Xỉu 🧋",
        "large_image": "rpc_logo",
        "large_text":  "⚡ NEON RPC v2",
    }
