
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "helpers"))

import bridge_server
from asset_mapper import get_language_asset
from utils import truncate
from logger import get_logger

log = get_logger("VSCode")

PRIORITY = 3


def is_running() -> bool:
    """Active when the extension is connected AND reporting a focused editor."""
    server = bridge_server.get_server()
    if server is None:
        return False
    state = server.get_state()
    if not state:
        return False
    # Consider active only when VSCode window is focused with an open file
    return bool(state.get("file"))


def get_rpc() -> dict:
    server = bridge_server.get_server()
    state  = server.get_state() if server else None

    if not state:
        return _idle_rpc()

    file_name   = state.get("file", "")
    workspace   = state.get("workspace", "Workspace")
    language    = state.get("language", "")
    line        = state.get("line", 0)
    total_lines = state.get("totalLines", 0)
    errors      = state.get("errors", 0)
    warnings    = state.get("warnings", 0)
    message     = state.get("message", "")
    git_branch  = state.get("gitBranch", "")
    is_dirty    = state.get("isDirty", False)

    lang_info = get_language_asset(language)
    lang_name = lang_info["name"]
    asset_key = lang_info["asset"]

    # ── DETAILS line ──────────────────────────────────────────────────────
    dirty_marker = "● " if is_dirty else ""
    lines_text   = f" | {total_lines} dòng" if total_lines else ""
    details      = truncate(f"📝 {dirty_marker}{file_name}{lines_text}", 128)

    # ── STATE line ────────────────────────────────────────────────────────
    if errors > 0 and warnings > 0:
        diag_prefix = f"❌{errors} ⚠{warnings}"
        if message:
            state_str = truncate(f"{diag_prefix} | L{line}: {message}", 128)
        else:
            state_str = f"{diag_prefix} | L{line}"
    elif errors > 0:
        if message:
            state_str = truncate(f"❌ L{line}: {message}", 128)
        else:
            state_str = f"❌ {errors} error{'s' if errors != 1 else ''} | L{line}"
    elif warnings > 0:
        state_str = truncate(f"⚠ {warnings} warning{'s' if warnings != 1 else ''} | L{line}", 128)
    else:
        state_str = f"✨ No Errors | {lang_name} L{line}"

    # Append git branch if available
    if git_branch:
        state_str = truncate(f"{state_str}  [{git_branch}]", 128)

    # ── large_text ────────────────────────────────────────────────────────
    large_text = truncate(f"ĐANG EDIT {file_name.upper()} — {workspace}", 128)

    log.info(f"{file_name} L{line} | ❌{errors} ⚠{warnings}")

    return {
        "details":     details,
        "state":       state_str,
        "large_image": asset_key,
        "large_text":  large_text,
    }


def _idle_rpc() -> dict:
    return {
        "details":     "💻 Không edit file",
        "state":       "📂 Workspace mở",
        "large_image": "vscode_logo",
        "large_text":  "VISUAL STUDIO CODE",
    }