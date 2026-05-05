#!/bin/bash

# 获取当前项目的绝对路径
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

echo "🔄 Restarting Long River Agent System (v2 - Silent Mode)..."

# --- 新增：清理旧进程 ---
echo "🧹 Cleaning up orphaned processes..."
pkill -f agent_host.py 2>/dev/null
pkill -f central_server.py 2>/dev/null
sleep 1
# ----------------------

# 端口检测函数，自动寻找空闲端口
get_free_port() {
    local port=$1
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        port=$((port+98))
    done
    echo $port
}

# 分配核心组件端口
CENTRAL_PORT=$(get_free_port 8000)
FRONTEND_PORT=$(get_free_port 5173)

echo "🎯 Core Ports:"
echo "  - Central:  $CENTRAL_PORT"
echo "  - Frontend: $FRONTEND_PORT"

# 导出环境变量
export PORT=$CENTRAL_PORT
export CENTRAL_SERVER_URL="http://127.0.0.1:$CENTRAL_PORT"
export VITE_CENTRAL_URL=$CENTRAL_SERVER_URL

# 定义退出时的清理函数
cleanup() {
    echo -e "\n🛑 Stopping all services..."
    # 捕获当前脚本的 PID
    local self_pid=$$
    # 杀掉除自己以外的所有同组进程
    trap - SIGINT SIGTERM # 防止递归
    kill -TERM -0 2>/dev/null
    echo "Done."
    exit 0
}

# 捕获 Ctrl+C
trap cleanup SIGINT SIGTERM

echo "🚀 Starting services in background..."

# 1. 启动中央服务器
PORT=$CENTRAL_PORT uv run python central_server.py > "$LOG_DIR/central.log" 2>&1 &
echo "  - [$CENTRAL_PORT] Central Server (Log: logs/central.log)"
sleep 2

# 2. 自动发现并启动所有 Agent
AGENT_START_PORT=5001
for agent_dir in */; do
    agent_dir=${agent_dir%/}
    # 检查目录下是否存在 AgentCard.json
    if [ -f "$agent_dir/AgentCard.json" ]; then
        AGENT_PORT=$(get_free_port $AGENT_START_PORT)
        # 更新下一个搜索起点
        AGENT_START_PORT=$((AGENT_PORT + 1))
        
        CENTRAL_SERVER_URL=$CENTRAL_SERVER_URL uv run python agent_host.py $AGENT_PORT "./$agent_dir" > "$LOG_DIR/${agent_dir}.log" 2>&1 &
        echo "  - [$AGENT_PORT] Agent: ${agent_dir} (Log: logs/${agent_dir}.log)"
    fi
done

# 3. 启动前端
(cd frontend && npm run dev -- --port $FRONTEND_PORT) > "$LOG_DIR/frontend.log" 2>&1 &
echo "  - [$FRONTEND_PORT] Frontend UI    (Log: logs/frontend.log)"

echo -e "\n✅ All services are running."
echo "👉 Open: http://localhost:$FRONTEND_PORT"
echo "💡 Use the Terminal tab in the Web UI to interact with agents."
echo "按下 Ctrl+C 可停止所有服务。"

# 保持脚本运行，等待所有后台进程
wait
