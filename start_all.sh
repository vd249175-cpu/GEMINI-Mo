#!/bin/bash

# 获取当前项目的绝对路径
PROJECT_ROOT=$(pwd)

echo "🚀 Starting Long River Agent System..."

# 1. 在新窗口启动中央服务器
osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python3 central_server.py\""
echo "  - Central Server starting on port 8000..."
sleep 2

# 2. 在新窗口启动 Worker Agent
osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python3 agent_host.py 5001 ./worker\""
echo "  - Worker Agent starting on port 5001..."

# 3. 在新窗口启动 Judge Agent
osascript -e "tell application \"Terminal\" to do script \"cd '$PROJECT_ROOT' && python3 agent_host.py 5002 ./judge\""
echo "  - Judge Agent starting on port 5002..."

echo "✅ All components are starting in separate windows."
echo "Wait for the 'Registered with Central Server' message in each terminal."
