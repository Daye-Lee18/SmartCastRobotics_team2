@echo off
REM 3 서비스 동시 실행 (Windows) - 각 서비스를 별도 cmd 창에 띄움.
setlocal
set ROOT=%~dp0..

start "SmartCast Backend" cmd /k "%ROOT%\scripts\run-backend.bat"
timeout /t 3 /nobreak >nul
start "SmartCast PyQt"    cmd /k "%ROOT%\scripts\run-pyqt.bat"
start "SmartCast Web"     cmd /k "%ROOT%\scripts\run-web.bat"

echo -^> 3 서비스 시작됨 (각 cmd 창 확인)
echo    중단: scripts\stop-all.bat 또는 각 창 Ctrl+C
endlocal
