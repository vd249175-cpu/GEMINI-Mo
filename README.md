<p align="center">
  <img src="docs/logo.png" width="120" alt="GEMINI-MO Logo" />
</p>

<h1 align="center">GEMINI-MO</h1>
<p align="center">A visual multi-agent console — let your Gemini CLI agents talk to each other, send files, and collaborate autonomously</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README_zh-CN.md">中文</a>
</p>

---

## What is this?

GEMINI-MO lets you run multiple [Gemini CLI](https://github.com/google-gemini/gemini-cli) agents side by side and **wire them together into a collaborative network**.

Each agent runs in `--yolo` mode with access to MCP tools that allow it to:
- 📨 **Send messages** to any other online agent by name
- 📁 **Send files** (as base64 payloads) — automatically written to the recipient's workspace
- 📬 **Receive messages asynchronously** — queued and delivered when the target comes back online

> **Example:** Ask a `worker` agent to write code, then have it automatically forward the result to a `judge` agent for review — zero copy-paste, zero manual handoff.

---

## Screenshots

<table>
  <tr>
    <td><img src="docs/screenshots/23-04.png" alt="Network View" /></td>
    <td><img src="docs/screenshots/24.png" alt="Terminal View" /></td>
  </tr>
  <tr>
    <td align="center"><em>Network topology — drag agents, create spaces and connect them</em></td>
    <td align="center"><em>Live terminal — directly interact with each Gemini CLI agent</em></td>
  </tr>
</table>

---

## Features

- 💬 **Agent-to-Agent Messaging** — send messages and files between agents via the central server
- 🕸️ **Visual Network Graph** — drag-and-drop layout, persistent positions, connection lines colored by space
- 🖥️ **Embedded Terminal** — full xterm.js terminal wired to each agent's PTY, with truecolor support
- 🤖 **Multi-Agent Management** — start, stop, clone and delete agents from the UI
- 🌐 **Communication Spaces** — group agents into named spaces to control who talks to whom
- 🌙 **Dark / Light Theme** — one-click toggle, persisted in localStorage
- 🌏 **i18n** — English / Chinese UI (default: English)
- ⚡ **Dynamic Port Allocation** — auto-detects free ports, no manual configuration needed

---

## Quick Start

### macOS / Linux

**First-time setup** (installs `uv`, Python deps, Node deps, then starts everything):
```bash
chmod +x start.sh && ./start.sh
```

**Fast restart** (skip dependency install, just start services):
```bash
chmod +x start_all.sh && ./start_all.sh
```

### Windows

**First-time setup** (auto-installs `uv` via PowerShell if missing):
```cmd
start.bat
```

---

## Requirements

| Dependency | Version | Notes |
|---|---|---|
| Python | ≥ 3.10 | Managed by `uv` |
| Node.js | ≥ 18 | For the frontend |
| [uv](https://github.com/astral-sh/uv) | latest | Auto-installed by `start.sh` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | latest | Install via `npm i -g @google/gemini-cli` |

---

## Architecture

```
Browser (React UI)
      │
      ▼
Central Server (FastAPI :8000)
      │
      ├── Worker Agent (:5001+)
      │       └── gemini --yolo  (PTY)
      │
      └── Judge Agent  (:5002+)
              └── gemini --yolo  (PTY)
```

Each agent runs inside a PTY managed by `agent_host.py`, which exposes a WebSocket terminal and registers itself with the central server on startup.

---

## Project Structure

```
character/
├── central_server.py     # Central FastAPI server — routes messages, manages agents
├── agent_host.py         # Per-agent FastAPI host — spawns Gemini CLI in a PTY
├── worker/               # Worker agent workspace
├── judge/                # Judge agent workspace
├── frontend/             # React + Vite UI
│   └── src/
│       ├── App.jsx       # Main UI component
│       └── App.css       # Design system + dark theme
├── start.sh              # One-click setup & start (macOS/Linux)
├── start.bat             # One-click setup & start (Windows)
├── start_all.sh          # Fast restart (no dependency checks)
└── docs/
    ├── logo.png
    └── screenshots/
```
