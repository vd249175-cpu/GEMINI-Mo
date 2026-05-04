@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo     GEMINI-MO One-Click Start (Windows)
echo ==========================================

:: 1. Check and install uv
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [-] uv not found. Installing uv via PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if %ERRORLEVEL% neq 0 (
        echo [!] Failed to install uv. Please install manually: https://github.com/astral-sh/uv
        exit /b 1
    )
)

:: 2. Install Python dependencies
echo [-] Installing Python dependencies...
uv sync
if %ERRORLEVEL% neq 0 (
    echo [!] Failed to install Python dependencies.
    exit /b 1
)

:: 3. Check npm and install frontend dependencies
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] npm not found. Please install Node.js from https://nodejs.org/
    exit /b 1
)

echo [-] Installing frontend dependencies...
cd frontend
call npm install
if %ERRORLEVEL% neq 0 (
    echo [!] Failed to install frontend dependencies.
    exit /b 1
)
cd ..

echo ==========================================
echo     Starting Services...
echo ==========================================

:: Find free ports using PowerShell helper function
for /f %%p in ('powershell -NoProfile -Command "$port=8000; while((Test-NetConnection localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue).TcpTestSucceeded){$port+=98}; $port"') do set CENTRAL_PORT=%%p
for /f %%p in ('powershell -NoProfile -Command "$port=5001; while((Test-NetConnection localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue).TcpTestSucceeded){$port+=98}; $port"') do set WORKER_PORT=%%p
for /f %%p in ('powershell -NoProfile -Command "$port=5002; while((Test-NetConnection localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue).TcpTestSucceeded){$port+=98}; $port"') do set JUDGE_PORT=%%p
for /f %%p in ('powershell -NoProfile -Command "$port=5173; while((Test-NetConnection localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue).TcpTestSucceeded){$port+=98}; $port"') do set FRONTEND_PORT=%%p

echo [-] Ports: Central=%CENTRAL_PORT%  Worker=%WORKER_PORT%  Judge=%JUDGE_PORT%  Frontend=%FRONTEND_PORT%

set CENTRAL_SERVER_URL=http://127.0.0.1:%CENTRAL_PORT%

:: Start services in separate windows
start "Central Server" cmd /c "set PORT=%CENTRAL_PORT% && uv run python central_server.py"
timeout /t 2 >nul

start "Worker Agent" cmd /c "set CENTRAL_SERVER_URL=%CENTRAL_SERVER_URL% && uv run python agent_host.py %WORKER_PORT% ./worker"
start "Judge Agent" cmd /c "set CENTRAL_SERVER_URL=%CENTRAL_SERVER_URL% && uv run python agent_host.py %JUDGE_PORT% ./judge"

cd frontend
start "Frontend" cmd /c "npm run dev -- --port %FRONTEND_PORT%"
cd ..

echo.
echo [+] All services are starting in separate windows.
echo [+] Open: http://localhost:%FRONTEND_PORT%
echo [+] Close the opened windows to stop services.
