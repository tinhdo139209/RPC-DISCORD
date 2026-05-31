import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "helpers"))

import re
from utils import is_process_running, get_process_cmdline, truncate
from logger import get_logger

log = get_logger("Blender")

PRIORITY = 2

_BLENDER_NAMES = ["blender", "blender.exe"]

# Workspace hints that indicate Python / scripting mode
_SCRIPTING_HINTS = ["scripting", "text editor", "python", "script"]
_SCENE_HINTS     = ["scene", "render", "compositor", "shader", "geometry nodes"]


def is_running() -> bool:
    found, name = is_process_running(_BLENDER_NAMES)
    if found:
        log.info(f"Detected: {name}")
    return found


def get_rpc() -> dict:
    cmdline = get_process_cmdline(_BLENDER_NAMES) or ""

    # Extract .blend filename from command line
    blend_file = _extract_blend(cmdline)
    project    = _project_name(blend_file)
    workspace  = _detect_workspace(cmdline)
    is_scripting = any(h in cmdline.lower() for h in _SCRIPTING_HINTS)

    # ── DETAILS ──────────────────────────────────────────────────────────
    if blend_file:
        details = truncate(f"🎨 {blend_file}", 128)
    else:
        details = "🎨 Blender"

    # ── STATE ─────────────────────────────────────────────────────────────
    if is_scripting:
        state      = truncate(f"🐍 Blender Python | {project}", 128)
        large_image = "python_logo"
        large_text  = f"BLENDER PYTHON — {project.upper()}"
    elif workspace:
        state       = truncate(f"🧊 {workspace} | {project}", 128)
        large_image = "blender_logo"
        large_text  = f"BLENDER — {project.upper()}"
    else:
        state       = truncate(f"🧊 {project}", 128)
        large_image = "blender_logo"
        large_text  = f"BLENDER — {project.upper()}"

    log.info(f"{blend_file or 'no file'} | scripting={is_scripting}")

    return {
        "details":     details,
        "state":       state,
        "large_image": large_image,
        "large_text":  large_text,
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_blend(cmdline: str) -> str:
    """Pull the .blend filename from the process command line."""
    match = re.search(r'[\\/]?([^\\/\s"\']+\.blend)', cmdline, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _project_name(blend_file: str) -> str:
    if blend_file:
        return blend_file.replace(".blend", "")
    return "Unknown Project"


def _detect_workspace(cmdline: str) -> str:
    cl = cmdline.lower()
    for hint in _SCRIPTING_HINTS:
        if hint in cl:
            return "Scripting"
    for hint in _SCENE_HINTS:
        if hint in cl:
            return "Scene Editing"
    return ""
