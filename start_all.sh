#!/bin/bash

# 获取当前项目的绝对路径
PROJECT_ROOT=$(pwd)
LOG_DIR="$PROJECT_ROOT/logs"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

echo "🔄 Restarting Long River Agent System (v2 - Silent Mode)..."

# 1. 清理现有进程
PORTS=(8000 5001 5002 5173)
for PORT in "${PORTS[@]}"; do
    PIDS=$(lsof -ti:$PORT)
    if [ ! -z "$PIDS" ]; then
        echo "  - Cleaning up port $PORT..."
        for PID in $PIDS; do
            kill -9 $PID 2>/dev/null
        done
    fi
done

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
uv run python central_server.py > "$LOG_DIR/central.log" 2>&1 &
echo "  - [8000] Central Server (Log: logs/central.log)"
sleep 2

# 2. 启动 Worker Agent
uv run python agent_host.py 5001 ./worker > "$LOG_DIR/worker.log" 2>&1 &
echo "  - [5001] Worker Agent   (Log: logs/worker.log)"

# 3. 启动 Judge Agent
uv run python agent_host.py 5002 ./judge > "$LOG_DIR/judge.log" 2>&1 &
echo "  - [5002] Judge Agent    (Log: logs/judge.log)"

# 4. 启动前端
(cd frontend && npm run dev) > "$LOG_DIR/frontend.log" 2>&1 &
echo "  - [5173] Frontend UI    (Log: logs/frontend.log)"

echo -e "\n✅ All services are running."
echo "👉 Open: http://localhost:5173"
echo "💡 Use the Terminal tab in the Web UI to interact with agents."
echo "按下 Ctrl+C 可停止所有服务。"

# 保持脚本运行，等待所有后台进程
wait
