@echo off
setlocal

echo ==========================================
echo     Character Console One-Click Start
echo ==========================================

:: 1. Check and install uv
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [-] uv not found. Please install uv using: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo [-] Or download it manually from https://github.com/astral-sh/uv
    exit /b 1
)

:: 2. Install Python dependencies
echo [-] Installing Python dependencies...
uv sync

:: 3. Check npm and install frontend dependencies
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] npm not found. Please install Node.js first!
    exit /b 1
)

echo [-] Installing frontend dependencies...
cd frontend
call npm install
cd ..

echo ==========================================
echo     Starting Services...
echo ==========================================

:: Start backend in a new window
echo [-] Starting central server (backend)...
start "Central Server (Backend)" cmd /c "uv run central_server.py"

:: Start frontend in a new window
echo [-] Starting frontend server...
cd frontend
start "Frontend Server" cmd /c "npm run dev"
cd ..

echo [-] Services are starting in separate windows.
echo [-] To stop the services, simply close those command prompt windows.
