# 角色控制台 (Character Console)

[English](README.md) | 中文

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
