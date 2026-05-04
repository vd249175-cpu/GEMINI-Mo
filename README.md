# Character Console / 角色控制台

[English](#english) | [中文](#中文)

---

## English

### Overview
This project provides a comprehensive multi-agent control console with both backend operations and a frontend visual interface. The default language of the application (including the frontend) is **English**.

### Installation & Quick Start

We highly recommend using `uv` to manage the Python environment and dependencies for this project.

**1. Install Dependencies**
Ensure you have `uv` installed, then run:
```bash
uv sync
```

**2. Start the Application**
To start the backend server and services:
```bash
uv run central_server.py
```
*(Make sure to also start the frontend application using standard Node.js/Vite commands if applicable, for example: `npm run dev` in the `frontend` directory).*

### Note
The `handswriter-image-gen` skill has been removed from git tracking and remains a local-only capability in the environment.

---

## 中文

### 概述
本项目提供了一个功能全面的多智能体控制台，包含后端服务与前端可视化界面。应用程序（包括前端）的默认语言已设为**英文 (English)**。

### 安装与启动

推荐使用 `uv` 来管理本项目的 Python 环境和依赖包。

**1. 安装依赖**
请确保你已经安装了 `uv`，然后在项目根目录下运行：
```bash
uv sync
```

**2. 启动应用**
启动后端服务器与相关服务：
```bash
uv run central_server.py
```
*（如需启动前端页面，请进入 `frontend` 目录运行相应的前端启动命令，例如 `npm run dev`）。*

### 备注
`handswriter-image-gen` 技能已被移出 Git 追踪列表，现在作为本地独立功能保留。
