@echo off
REM Backend FastAPI :8000 실행 (Windows).
setlocal
set ROOT=%~dp0..
cd /d "%ROOT%\server\main_service"

if not exist .venv (echo X .venv 없음. scripts\setup.bat 먼저 실행. & exit /b 1)
if not exist .env.local (echo X .env.local 없음. setup.bat 실행 후 비밀번호 입력. & exit /b 1)

call .venv\Scripts\activate.bat
set PYTHONPATH=src
if "%PORT%"=="" set PORT=8000
if "%HOST%"=="" set HOST=0.0.0.0

echo -^> FastAPI on http://%HOST%:%PORT% (Ctrl+C 종료)
uvicorn main_service.app.main:app --host %HOST% --port %PORT% --env-file .env.local --reload
endlocal
