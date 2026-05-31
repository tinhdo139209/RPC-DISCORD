# NEON VSCord — VSCode Extension

Real-time editor state bridge for **NEON RPC v2**.

## What it does

Pushes live editor data to the NEON RPC Python engine over a local WebSocket connection:

- Active file name & workspace
- Language ID (Python, TypeScript, Lua, …)
- Cursor line & total lines
- Error and warning counts (from the Problems panel)
- First diagnostic message
- Git branch name
- Dirty (unsaved) state
- Window focus state

## Requirements

- NEON RPC v2 Python engine running (`python main.py`)
- VSCode 1.85+

## Setup

```bash
cd extension/neon-vscord
npm install
npm run compile
```

Then press **F5** in VSCode to launch the Extension Development Host, or install the `.vsix` package directly.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `neonVscord.port` | `7878` | Bridge WebSocket port |
| `neonVscord.enabled` | `true` | Toggle presence |
| `neonVscord.updateInterval` | `2000` | Poll interval (ms) |

Port must match `bridge_port` in `config.json`.

## Status bar

The **NEON** indicator in the status bar shows connection state:

- `$(pulse) NEON` — Connected & sending
- `$(sync~spin) NEON` — Connecting…
- `$(circle-slash) NEON` — Disconnected (auto-reconnects)
- `$(eye-closed) NEON` — Disabled

Click it to toggle presence on/off.
