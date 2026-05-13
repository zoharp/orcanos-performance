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
