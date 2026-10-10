@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Madar.ps1" %*
set "MADAR_EXIT=%ERRORLEVEL%"
if not "%MADAR_EXIT%"=="0" echo MADAR startup failed. Review the redacted PASS/FAIL report above.
pause
exit /b %MADAR_EXIT%
