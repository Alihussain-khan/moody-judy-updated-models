@echo off
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000
