@echo off
REM Right-click -> Run as administrator
cd /d "%~dp0"
if not exist psexec.exe (
  echo Download PsExec from Microsoft Sysinternals and put psexec.exe in this folder.
  pause & exit /b 1
)
for /f %%i in ('powershell -NoProfile -Command "(Get-Process -Id $PID).SessionId"') do set SID=%%i
for /f "delims=" %%p in ('where python') do (set PY=%%p& goto :run)
echo Python not found. Install it from python.org (tick "Add to PATH").
pause & exit /b 1
:run
echo Starting in session %SID% using %PY%
psexec.exe -accepteula -s -i %SID% "%PY%" "%~dp0pc_server.py"
pause
