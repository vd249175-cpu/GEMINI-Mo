# Character Console / 角色控制台

[English](#english) | [中文](#中文)

---

## English

### Overview
This project provides a comprehensive multi-agent control console with both backend operations and a frontend visual interface. The default language of the application (including the frontend) is **English**.

### Installation & Quick Start

We highly recommend using the provided one-click startup scripts. These scripts will automatically install `uv` (if missing), install all Python and Node.js dependencies, and start both the backend and frontend servers simultaneously.

**For macOS / Linux:**
```bash
./start.sh
```

**For Windows:**
```cmd
start.bat
```

*(If you prefer manual setup, simply run `uv sync` and `npm install` in the `frontend` directory, then start `central_server.py` and `npm run dev` separately).*

### Note
The `handswriter-image-gen` skill has been removed from git tracking and remains a local-only capability in the environment.

---

## 中文

### 概述
本项目提供了一个功能全面的多智能体控制台，包含后端服务与前端可视化界面。应用程序（包括前端）的默认语言已设为**英文 (English)**。

### 安装与启动

推荐使用项目提供的一键启动脚本。这些脚本会自动检测并安装 `uv`（如果未安装），安装所有的 Python 和 Node.js 依赖，并同时启动后端服务器和前端应用。

**对于 macOS / Linux 用户：**
```bash
./start.sh
```

**对于 Windows 用户：**
```cmd
start.bat
```

*（如果你更喜欢手动启动，可以分别执行 `uv sync` 和前端目录下的 `npm install`，然后单独启动 `central_server.py` 和 `npm run dev`）。*

### 备注
`handswriter-image-gen` 技能已被移出 Git 追踪列表，现在作为本地独立功能保留。
