<p align="center">
  <img src="docs/logo.png" width="120" alt="GEMINI-MO Logo" />
</p>

<h1 align="center">GEMINI-MO</h1>
<p align="center">可视化多智能体控制台，用于编排 Gemini CLI 代理</p>

<p align="center">
  <a href="README.md">English</a> | 中文
</p>

---

## 截图预览

<table>
  <tr>
    <td><img src="docs/screenshots/23-04.png" alt="网络视图" /></td>
    <td><img src="docs/screenshots/24.png" alt="终端视图" /></td>
  </tr>
  <tr>
    <td align="center"><em>网络拓扑图 — 可拖拽 Agent 节点，创建通讯空间并连线</em></td>
    <td align="center"><em>嵌入终端 — 直接与每个 Gemini CLI Agent 实时交互</em></td>
  </tr>
</table>

---

## 功能亮点

- 🕸️ **可视化网络图谱** — 拖拽布局，位置持久化，连线按空间高亮着色
- 🖥️ **嵌入式终端** — 每个 Agent 独享 xterm.js 终端，完整 PTY 支持，真彩色渲染
- 🤖 **多智能体管理** — 通过 UI 直接启动、停止、克隆和删除 Agent
- 💬 **Agent 间通讯** — Gemini CLI Agent 可以通过中央服务器直接向其他 Agent 发送消息和文件，实现真正的多智能体协作工作流
- 🌐 **通讯空间** — 将 Agent 分组，精准管控它们之间的通讯范围
- 🌙 **暗色 / 亮色主题** — 一键切换，记住你的偏好
- 🌏 **国际化** — 英文 / 中文界面（默认英文）
- ⚡ **动态端口分配** — 自动检测空闲端口，无需手动配置

---

## 快速启动

### macOS / Linux

**首次运行**（自动安装 `uv`、Python 依赖、Node 依赖，然后启动所有服务）：
```bash
chmod +x start.sh && ./start.sh
```

**快速重启**（跳过依赖检查，直接启动服务）：
```bash
chmod +x start_all.sh && ./start_all.sh
```

### Windows

**首次运行**（若未安装 `uv`，会通过 PowerShell 自动安装）：
```cmd
start.bat
```

---

## 环境依赖

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | ≥ 3.10 | 由 `uv` 自动管理 |
| Node.js | ≥ 18 | 用于前端 |
| [uv](https://github.com/astral-sh/uv) | 最新版 | `start.sh` 会自动安装 |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | 最新版 | 通过 `npm i -g @google/gemini-cli` 安装 |

---

## 项目结构

```
character/
├── central_server.py     # 中央 FastAPI 服务 — 路由消息、管理 Agent 生命周期
├── agent_host.py         # 单 Agent FastAPI 宿主 — 在 PTY 中运行 Gemini CLI
├── worker/               # Worker 智能体工作目录
├── judge/                # Judge 智能体工作目录
├── frontend/             # React + Vite 前端
│   └── src/
│       ├── App.jsx       # 主 UI 组件
│       └── App.css       # 设计系统 + 暗色主题
├── start.sh              # 一键安装并启动（macOS/Linux）
├── start.bat             # 一键安装并启动（Windows）
├── start_all.sh          # 快速重启（跳过依赖检查）
└── docs/
    ├── logo.png
    └── screenshots/
```

---

## Agent 间通讯机制

GEMINI-MO 的核心能力之一，是让**各个 Gemini CLI Agent 能够自主地互相通讯**。

每个 Agent 以 `--yolo` 模式运行，并通过 MCP 工具获得以下能力：
- 📨 **发送消息** — 可以按名称向任意在线 Agent 发送文本消息
- 📁 **发送文件** — 以 base64 格式将文件发送给其他 Agent，文件会自动写入对方的工作目录
- 📬 **异步接收** — 如果目标 Agent 当前离线，消息会被中央服务器缓存，等 Agent 上线后立即投递

这意味着你可以让 `worker` Agent 完成一项任务，并自动将结果转发给 `judge` Agent 进行审核 —— 完全无需人工介入复制粘贴。

---

## 架构说明

```
浏览器 (React UI)
      │
      ▼
中央服务器 (FastAPI :8000)
      │
      ├── Worker Agent (:5001+)
      │       └── gemini --yolo  (PTY)
      │
      └── Judge Agent  (:5002+)
              └── gemini --yolo  (PTY)
```

每个 Agent 通过 `agent_host.py` 运行在 PTY 内，暴露 WebSocket 终端，并在启动时自动向中央服务器注册。
