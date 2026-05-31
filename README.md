# ⚡ NEON RPC v2

> Multi-app Discord Rich Presence engine — Python + VSCode extension.

---

## Features

| Plugin   | Priority | Detection method                        |
|----------|----------|-----------------------------------------|
| FiveM    | 1        | Process scan + Discord IPC mirror       |
| Blender  | 2        | Process scan + cmdline `.blend` parsing |
| VSCode   | 3        | WebSocket bridge ← extension            |
| Idle     | 99       | Always-on fallback                      |

- **Real VSCode data** — file, language, cursor, diagnostics, git branch, dirty flag
- **No brute-force parsing** — zero window-title hacks, zero `os.walk`
- **FiveM RPC mirror** — reads Discord IPC to clone server presence + assets
- **Blender detection** — scripting vs scene mode, Python asset in script mode
- **Plugin priority system** — highest active plugin owns the presence
- **Robust connection** — pipe retry, auto-reconnect watchdog, heartbeat
- **Update throttle** — no Discord spam
- **Structured logging** — `[TAG] LEVEL message` with colour

---

## Project structure

```
neon-rpc-v2/
├── main.py               ← Core engine (start here)
├── rpc_client.py         ← Discord RPC wrapper + watchdog
├── bridge_server.py      ← WebSocket server for VSCode extension
├── logger.py             ← Tagged colour logger
├── config.json           ← All runtime settings
├── requirements.txt
│
├── plugins/
│   ├── vscode_bridge.py  ← VSCode plugin (uses bridge_server)
│   ├── blender_bridge.py ← Blender plugin
│   ├── fivem_bridge.py   ← FiveM hybrid plugin
│   └── idle.py           ← Fallback plugin
│
├── helpers/
│   ├── asset_mapper.py       ← Language/app → Discord asset key
│   ├── discord_pipe_reader.py← Discord IPC reader for FiveM mirror
│   └── utils.py              ← Process detection, throttle, sanitise
│
└── extension/
    └── neon-vscord/          ← VSCode extension
        ├── src/extension.ts
        ├── package.json
        └── tsconfig.json
```

---

## Setup

### 1. Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Discord application

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new application (or open your existing one)
3. Copy the **Application ID** → paste into `config.json` as `client_id`
4. Go to **Rich Presence → Art Assets** and upload all icons from `ASSET_CHECKLIST.md`

### 3. Configure

Edit `config.json`:

```json
{
  "client_id": "YOUR_APP_ID_HERE",
  "scan_interval": 3,
  "update_throttle": 5,
  "bridge_port": 7878
}
```

### 4. Run

```bash
python main.py
```

### 5. VSCode extension

```bash
cd extension/neon-vscord
npm install
npm run compile
```

- Press **F5** in VSCode to launch Extension Development Host, **or**
- Run `vsce package` then install the `.vsix`

The extension connects automatically on port `7878`.  
A **NEON** status bar item shows connection state.

---

## Config reference

| Key               | Default | Description                             |
|-------------------|---------|-----------------------------------------|
| `client_id`       | —       | Discord application ID                  |
| `scan_interval`   | 3       | Seconds between plugin polls            |
| `update_throttle` | 5       | Minimum seconds between RPC updates     |
| `bridge_port`     | 7878    | VSCode extension WebSocket port         |
| `small_image`     | online  | Status dot asset key                    |
| `plugins.*`       | —       | Enable/disable and set priority per plugin |

---

## Adding a custom plugin

1. Create `plugins/myplugin.py`
2. Define:
   ```python
   PRIORITY = 5   # lower = higher priority

   def is_running() -> bool:
       ...        # return True when your app is detected

   def get_rpc() -> dict:
       return {
           "details":     "...",
           "state":       "...",
           "large_image": "my_logo",
           "large_text":  "MY APP",
       }
   ```
3. Restart `main.py` — it auto-discovers plugins

---

## Logging

```
12:34:56 [RPC]     INFO    Connected to Discord (pipe=0)
12:34:57 [VSCode]  INFO    main.py L84 | ❌2 ⚠1
12:34:58 [FiveM]   INFO    Mirrored RPC from 'Mini City RP'
12:35:00 [Blender] INFO    city.blend | scripting=True
12:35:02 [Bridge]  INFO    VSCode extension connected from ('127.0.0.1', 54321)
```

---

## Discord RPC examples

**VSCode — coding with errors:**
```
DETAILS  📝 main.py | 534 dòng
STATE    ❌2 ⚠1 | L84: Undefined variable x
LARGE    python_logo
TEXT     ĐANG EDIT MAIN.PY — NeonRPC
```

**VSCode — clean:**
```
DETAILS  📝 app.ts | 120 dòng
STATE    ✨ No Errors | TypeScript L42  [main]
```

**FiveM — mirrored:**
```
DETAILS  🎮 Mini City RP
STATE    🚓 Đang Roleplay
LARGE    city_logo
```

**Blender scripting:**
```
DETAILS  🎨 city.blend
STATE    🐍 Blender Python | city
LARGE    python_logo
```

**Idle:**
```
DETAILS  💻 Coding by Roshi
STATE    🧋 Đang Uống Bạc Xỉu 🧋
```
