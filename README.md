# Character Console / 角色控制台

[English](#english) | [中文](#中文)

---

## English

### Overview
This project provides a comprehensive multi-agent control console with both backend operations and a frontend visual interface. The default language of the application (including the frontend) is **English**.

### Installation & Quick Start

**First-time Setup (Installs dependencies & starts services):**
Use the provided one-click script to install `uv`, Python dependencies, Node.js packages, and start all services.

**For macOS / Linux:**
```bash
./start.sh
```

**For Windows:**
```cmd
start.bat
```

**Fast Startup (Skip dependency checks):**
If you have already installed dependencies and just want to start the console quickly, use:
```bash
./start_all.sh
```

### Note
The `handswriter-image-gen` skill has been removed from git tracking and remains a local-only capability in the environment.

---

## 中文

### 概述
本项目提供了一个功能全面的多智能体控制台，包含后端服务与前端可视化界面。应用程序（包括前端）的默认语言已设为**英文 (English)**。

### 安装与启动

**首次运行（自动安装依赖并启动）：**
推荐使用一键脚本。它会自动检测并安装 `uv`，安装所有的 Python 和 Node.js 依赖，并启动所有服务。

**对于 macOS / Linux 用户：**
```bash
./start.sh
```

**对于 Windows 用户：**
```cmd
start.bat
```

**快速启动（跳过依赖检查）：**
如果你已经安装过依赖，只需要快速启动所有服务（包含后端、Frontend、Worker、Judge 等），请直接运行：
```bash
./start_all.sh
```

### 备注
`handswriter-image-gen` 技能已被移出 Git 追踪列表，现在作为本地独立功能保留。
