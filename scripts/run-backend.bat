@echo off
REM Backend FastAPI :8000 실행 (Windows).
setlocal
set ROOT=%~dp0..
cd /d "%ROOT%\server\main_service"

if not exist .venv (echo X .venv 없음. scripts\setup.bat 먼저 실행. & exit /b 1)
if not exist .env.local (echo X .env.local 없음. setup.bat 실행 후 비밀번호 입력. & exit /b 1)

call .venv\Scripts\activate.bat
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 'backend .venv 가 Python 3.11 미만입니다. Python 3.11 설치 후 scripts\\setup.bat 를 다시 실행하세요.')"
if errorlevel 1 exit /b 1
set PYTHONPATH=src\interface_service;src\main_service;src
if "%PORT%"=="" set PORT=8000
if "%HOST%"=="" set HOST=0.0.0.0

echo -^> FastAPI on http://%HOST%:%PORT% (Ctrl+C 종료)
uvicorn app.main:app --host %HOST% --port %PORT% --env-file .env.local --reload
endlocal
