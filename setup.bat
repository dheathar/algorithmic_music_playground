@echo off
REM ============================================================
REM  Signal Lab - Windows setup (run once, from the project folder)
REM  Requires: Python 3.12+  and  ffmpeg on PATH
REM  (SuperCollider is optional and installed separately, system-wide)
REM ============================================================
where py >nul 2>nul || (echo Python launcher 'py' not found - install Python 3.12+ from python.org & exit /b 1)
py -m venv .venv-win
call .venv-win\Scripts\python -m pip install --upgrade pip
call .venv-win\Scripts\pip install -r requirements.txt
echo.
echo Done. Start the lab with:  run.bat
echo (needs ffmpeg on PATH - get it from https://www.gyan.dev/ffmpeg/builds/ )
