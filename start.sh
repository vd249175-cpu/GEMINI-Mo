#!/bin/bash
set -e

echo "=========================================="
echo "    Character Console One-Click Start"
echo "=========================================="

# 1. Check and install uv
if ! command -v uv &> /dev/null; then
    echo "[-] uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the environment variables for uv to be available in this session
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
fi

# 2. Install Python dependencies
echo "[-] Installing Python dependencies..."
uv sync

# 3. Check and install Node.js dependencies
if ! command -v npm &> /dev/null; then
    echo "[!] npm not found. Please install Node.js first!"
    exit 1
fi

echo "[-] Installing frontend dependencies..."
cd frontend
npm install
cd ..

echo "=========================================="
echo "    Starting Services with start_all.sh..."
echo "=========================================="

./start_all.sh
