@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem ---- locate python ----------------------------------------------------
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  where py >nul 2>nul && set "PY=py"
)
if not defined PY (
  echo [ERROR] Python 3.9+ was not found on PATH.
  echo         Download it from https://www.python.org/downloads/
  echo         and tick "Add Python to PATH" during installation.
  echo.
  pause
  exit /b 1
)

rem ---- make sure yt-dlp is present ---------------------------------------
"%PY%" -c "import yt_dlp" >nul 2>nul
if errorlevel 1 if not exist ".venv\Scripts\yt-dlp.exe" (
  echo Installing yt-dlp ...
  echo.
  "%PY%" -m pip install -U yt-dlp
  echo.
)

rem ---- run ---------------------------------------------------------------
"%PY%" app.py %*
echo.
pause
