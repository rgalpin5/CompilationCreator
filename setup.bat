@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "CMD=%~1"
if "%CMD%"=="" set "CMD=setup"

set "PY="
call :find py -3.12
if defined PY goto :run
call :find py -3
if defined PY goto :run
call :find python
if defined PY goto :run

echo Python 3.12 or newer is required and was not found on PATH.
echo Install it from https://www.python.org/downloads/
exit /b 1

:run
%PY% -u scripts\dev.py %CMD%
exit /b %ERRORLEVEL%

:find
where %~1 >nul 2>&1
if errorlevel 1 exit /b 0
%* -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if errorlevel 1 exit /b 0
set "PY=%*"
exit /b 0
