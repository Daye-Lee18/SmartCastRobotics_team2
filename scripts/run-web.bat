@echo off
REM Next.js Web :3001 실행 (Windows).
setlocal
set ROOT=%~dp0..
cd /d "%ROOT%\ui\web"

if not exist node_modules (echo X node_modules 없음. scripts\setup.bat 먼저 실행. & exit /b 1)
if "%PORT%"=="" set PORT=3001

echo -^> Next.js dev on http://localhost:%PORT%
call npm run dev -- --port %PORT%
endlocal
