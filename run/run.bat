@echo off
setlocal

cd /d "%~dp0\.."

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m run.main
) else (
    start "" pythonw -m run.main
)

endlocal
exit /b 0