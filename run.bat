@echo off
setlocal enabledelayedexpansion

title Orcanos Performance Tool

echo.
echo ============================================================
echo  Orcanos Performance Tool
echo ============================================================
echo.

set BACKEND_PORT=8000
set FRONTEND_PORT=5173
set BACKEND_URL=http://localhost:%BACKEND_PORT%
set FRONTEND_URL=http://localhost:%FRONTEND_PORT%

cd /d "%~dp0"

REM ── Kill anything already on these ports ──────────────────────
echo [*] Stopping any previous processes...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %BACKEND_PORT% -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort %FRONTEND_PORT% -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul
timeout /t 2 /nobreak >nul

REM ── Clear Python cache ────────────────────────────────────────
for /d /r backend %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" 2>nul

REM ── Start Backend ─────────────────────────────────────────────
echo [1/2] Starting backend on port %BACKEND_PORT%...
start "Orcanos Backend" cmd /k "call .venv\Scripts\activate && python -m uvicorn backend.api:app --reload --port %BACKEND_PORT%"

REM ── Wait for backend to respond ───────────────────────────────
echo [*] Waiting for backend...
set /a tries=0
:wait_backend
set /a tries+=1
if %tries% gtr 30 (
    echo [!] Backend did not start. Check the backend window for errors.
    pause
    exit /b 1
)
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %BACKEND_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_backend
)
echo [OK] Backend ready.

REM ── Start Frontend ────────────────────────────────────────────
echo [2/2] Starting frontend on port %FRONTEND_PORT%...
start "Orcanos Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

REM ── Wait for frontend to respond ──────────────────────────────
echo [*] Waiting for frontend...
set /a tries=0
:wait_frontend
set /a tries+=1
if %tries% gtr 30 (
    echo [!] Frontend did not start. Check the frontend window for errors.
    goto open_browser
)
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort %FRONTEND_PORT% -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_frontend
)
echo [OK] Frontend ready.

:open_browser
echo.
echo [*] Opening browser...
start "" "%FRONTEND_URL%"

echo.
echo ============================================================
echo  App is running
echo ============================================================
echo  Frontend : %FRONTEND_URL%
echo  Backend  : %BACKEND_URL%
echo  API Docs : %BACKEND_URL%/docs
echo ============================================================
echo.
echo  Close this window or press Ctrl+C in either server
echo  window to stop.
echo.
pause
