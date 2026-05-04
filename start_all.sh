#!/bin/bash

# 获取当前项目的绝对路径
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

echo "🔄 Restarting Long River Agent System (v2 - Silent Mode)..."

# 端口检测函数，自动寻找空闲端口
get_free_port() {
    local port=$1
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; do
        port=$((port+98))
    done
    echo $port
}

# 分配端口
CENTRAL_PORT=$(get_free_port 8000)
WORKER_PORT=$(get_free_port 5001)
JUDGE_PORT=$(get_free_port 5002)
FRONTEND_PORT=$(get_free_port 5173)

echo "🎯 Assigned Ports:"
echo "  - Central:  $CENTRAL_PORT"
echo "  - Worker:   $WORKER_PORT"
echo "  - Judge:    $JUDGE_PORT"
echo "  - Frontend: $FRONTEND_PORT"

# 导出环境变量
export PORT=$CENTRAL_PORT
export CENTRAL_SERVER_URL="http://127.0.0.1:$CENTRAL_PORT"
export VITE_CENTRAL_URL=$CENTRAL_SERVER_URL

# 定义退出时的清理函数
cleanup() {
    echo -e "\n🛑 Stopping all services..."
    # 杀掉整个进程组
    kill 0
    exit
}

# 捕获 Ctrl+C
trap cleanup SIGINT SIGTERM

echo "🚀 Starting services in background..."

# 1. 启动中央服务器
PORT=$CENTRAL_PORT uv run python central_server.py > "$LOG_DIR/central.log" 2>&1 &
echo "  - [$CENTRAL_PORT] Central Server (Log: logs/central.log)"
sleep 2

# 2. 启动 Worker Agent
CENTRAL_SERVER_URL=$CENTRAL_SERVER_URL uv run python agent_host.py $WORKER_PORT ./worker > "$LOG_DIR/worker.log" 2>&1 &
echo "  - [$WORKER_PORT] Worker Agent   (Log: logs/worker.log)"

# 3. 启动 Judge Agent
CENTRAL_SERVER_URL=$CENTRAL_SERVER_URL uv run python agent_host.py $JUDGE_PORT ./judge > "$LOG_DIR/judge.log" 2>&1 &
echo "  - [$JUDGE_PORT] Judge Agent    (Log: logs/judge.log)"

# 4. 启动前端
(cd frontend && npm run dev -- --port $FRONTEND_PORT) > "$LOG_DIR/frontend.log" 2>&1 &
echo "  - [$FRONTEND_PORT] Frontend UI    (Log: logs/frontend.log)"

echo -e "\n✅ All services are running."
echo "👉 Open: http://localhost:$FRONTEND_PORT"
echo "💡 Use the Terminal tab in the Web UI to interact with agents."
echo "按下 Ctrl+C 可停止所有服务。"

# 保持脚本运行，等待所有后台进程
wait
