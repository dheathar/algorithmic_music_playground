@echo off
REM Start the Signal Lab locally -> open http://127.0.0.1:7700/
if not exist .venv-win\Scripts\uvicorn.exe (echo Run setup.bat first. & exit /b 1)
echo Signal Lab at http://127.0.0.1:7700/   (Ctrl+C to stop)
call .venv-win\Scripts\uvicorn server:app --port 7700
