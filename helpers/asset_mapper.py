"""
NEON RPC v2 — helpers/asset_mapper.py
Full language and application asset resolution with fallback.
"""

from logger import get_logger

log = get_logger("Assets")

# ── Language → Discord asset key ────────────────────────────────────────────
LANGUAGE_ASSETS: dict[str, dict] = {
    # Python family
    "python":      {"name": "Python",          "asset": "python_logo"},
    "py":          {"name": "Python",          "asset": "python_logo"},
    "blenderpython":{"name": "Blender Python", "asset": "python_logo"},

    # JavaScript family
    "javascript":  {"name": "JavaScript",      "asset": "javascript_logo"},
    "js":          {"name": "JavaScript",      "asset": "javascript_logo"},
    "javascriptreact": {"name": "React JSX",   "asset": "react_logo"},
    "jsx":         {"name": "React JSX",       "asset": "react_logo"},

    # TypeScript family
    "typescript":  {"name": "TypeScript",      "asset": "typescript_logo"},
    "ts":          {"name": "TypeScript",      "asset": "typescript_logo"},
    "typescriptreact": {"name": "React TSX",   "asset": "react_logo"},
    "tsx":         {"name": "React TSX",       "asset": "react_logo"},

    # Web
    "html":        {"name": "HTML",            "asset": "html_logo"},
    "css":         {"name": "CSS",             "asset": "css_logo"},
    "scss":        {"name": "SCSS",            "asset": "css_logo"},
    "sass":        {"name": "Sass",            "asset": "css_logo"},

    # Data / config
    "json":        {"name": "JSON",            "asset": "json_logo"},
    "yaml":        {"name": "YAML",            "asset": "yaml_logo"},
    "yml":         {"name": "YAML",            "asset": "yaml_logo"},
    "toml":        {"name": "TOML",            "asset": "json_logo"},
    "xml":         {"name": "XML",             "asset": "xml_logo"},

    # Scripting
    "lua":         {"name": "Lua",             "asset": "lua_logo"},
    "shellscript": {"name": "Shell",           "asset": "shell_logo"},
    "sh":          {"name": "Shell",           "asset": "shell_logo"},
    "bash":        {"name": "Bash",            "asset": "shell_logo"},
    "powershell":  {"name": "PowerShell",      "asset": "shell_logo"},

    # Systems
    "c":           {"name": "C",               "asset": "c_logo"},
    "cpp":         {"name": "C++",             "asset": "cpp_logo"},
    "c++":         {"name": "C++",             "asset": "cpp_logo"},
    "csharp":      {"name": "C#",              "asset": "csharp_logo"},
    "cs":          {"name": "C#",              "asset": "csharp_logo"},
    "rust":        {"name": "Rust",            "asset": "rust_logo"},
    "go":          {"name": "Go",              "asset": "go_logo"},
    "swift":       {"name": "Swift",           "asset": "swift_logo"},
    "kotlin":      {"name": "Kotlin",          "asset": "kotlin_logo"},

    # JVM
    "java":        {"name": "Java",            "asset": "java_logo"},

    # Web back-end
    "php":         {"name": "PHP",             "asset": "php_logo"},
    "ruby":        {"name": "Ruby",            "asset": "ruby_logo"},

    # Database
    "sql":         {"name": "SQL",             "asset": "sql_logo"},

    # Docs
    "markdown":    {"name": "Markdown",        "asset": "markdown_logo"},
    "md":          {"name": "Markdown",        "asset": "markdown_logo"},
    "plaintext":   {"name": "Plain Text",      "asset": "code_logo"},
    "text":        {"name": "Plain Text",      "asset": "code_logo"},
}

# ── Application asset keys ───────────────────────────────────────────────────
APP_ASSETS: dict[str, str] = {
    "vscode":   "vscode_logo",
    "blender":  "blender_logo",
    "fivem":    "fivem_logo",
    "roleplay": "roleplay_logo",
    "city":     "city_logo",
    "idle":     "rpc_logo",
    "default":  "rpc_logo",
    "code":     "code_logo",
}

_FALLBACK_ASSET = "code_logo"
_FALLBACK_NAME  = "Code"


def get_language_asset(language_id: str) -> dict:
    """
    Resolve a VSCode languageId (or file extension) to {name, asset}.
    Falls back to code_logo with a warning log if unknown.
    """
    key  = language_id.lower().strip()
    info = LANGUAGE_ASSETS.get(key)
    if info:
        return info.copy()

    log.warning(f"Unknown language '{language_id}' — using fallback asset '{_FALLBACK_ASSET}'")
    return {"name": key.upper() or _FALLBACK_NAME, "asset": _FALLBACK_ASSET}


def get_app_asset(app: str) -> str:
    """Return the Discord asset key for a given application name."""
    key   = app.lower().strip()
    asset = APP_ASSETS.get(key, APP_ASSETS["default"])
    return asset


def resolve_server_asset(server_name: str) -> str:
    """
    Attempt to derive a Discord asset key from a FiveM server name.
    Returns best-guess key; caller should handle missing asset gracefully.
    """
    name_lower = server_name.lower()

    # Common keyword hints
    if any(k in name_lower for k in ["city", "urban", "streets"]):
        return "city_logo"
    if any(k in name_lower for k in ["roleplay", "rp", "role"]):
        return "roleplay_logo"
    if any(k in name_lower for k in ["cops", "police", "pd"]):
        return "fivem_logo"

    # Fallback
    log.warning(f"Cannot map server '{server_name}' to an asset — using fivem_logo")
    return "fivem_logo"
