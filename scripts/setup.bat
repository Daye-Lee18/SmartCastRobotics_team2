@echo off
REM Windows 설치 자동화 — 모든 모듈 venv + 의존성 + .env.local 템플릿.
setlocal enabledelayedexpansion

set ROOT=%~dp0..
cd /d "%ROOT%"

echo [setup] python/node 점검
where python >nul 2>&1 || (echo X python 미설치 https://python.org & exit /b 1)
where node   >nul 2>&1 || (echo X node 미설치 https://nodejs.org   & exit /b 1)
where npm    >nul 2>&1 || (echo X npm 미설치                       & exit /b 1)

echo [1/3] server/main_service venv + 의존성
cd /d "%ROOT%\server\main_service"
if not exist .venv (python -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
call .venv\Scripts\deactivate.bat
if not exist .env.local (
    copy .env.example .env.local >nul
    echo   .env.local 생성됨 - 비밀번호 입력 필요
)

echo [2/3] ui/pyqt/factory_operator venv + 의존성
cd /d "%ROOT%\ui\pyqt\factory_operator"
if not exist .venv (python -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
call .venv\Scripts\deactivate.bat
if not exist .env.local (copy .env.example .env.local >nul)

echo [3/3] ui/web npm install
cd /d "%ROOT%\ui\web"
call npm install --silent --no-audit --no-fund
if not exist .env.local (copy .env.example .env.local >nul)

cd /d "%ROOT%"
echo.
echo 완료. 다음 단계:
echo   1) server\main_service\.env.local 의 DATABASE_URL 비밀번호 입력
echo   2) scripts\run-all.bat  (또는 개별 run-backend / run-pyqt / run-web)
endlocal
