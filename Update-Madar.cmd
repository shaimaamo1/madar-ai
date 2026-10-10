@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update-Madar.ps1" %*
set "MADAR_EXIT=%ERRORLEVEL%"
if not "%MADAR_EXIT%"=="0" echo MADAR update stopped safely. Review the redacted PASS/FAIL report above.
pause
exit /b %MADAR_EXIT%
