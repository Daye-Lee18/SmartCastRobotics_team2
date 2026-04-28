@echo off
REM 3 서비스 중단 (Windows) - 포트별 프로세스 kill.
setlocal

for %%P in (8000 50051 3001) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do (
        echo   port %%P: PID %%a kill
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM PyQt - 명령으로 추적
for /f "tokens=2" %%a in ('tasklist /FI "WINDOWTITLE eq SmartCast*"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo 완료
endlocal
