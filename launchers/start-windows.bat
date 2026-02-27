@echo off
setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\.."

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 scripts\start-standalone.py
  goto :eof
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python scripts\start-standalone.py
  goto :eof
)

echo Python is required. Install Python 3.10, 3.11, or 3.12.
exit /b 1
