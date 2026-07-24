@echo off
setlocal

cd /d "%~dp0\.."

echo ============================================================
echo Sea++ Compiler - Terminal Runner
echo ============================================================
echo.

set /p "INPUT_FILE=Enter Sea++ input file path: "

if "%INPUT_FILE%"=="" (
    echo.
    echo Error: Input file path cannot be empty.
    echo.
    pause
    exit /b 1
)

echo.
echo Select compiler phase:
echo.
echo   1 - Phase 1: Lexer Only
echo   2 - Phase 2: Full Analysis
echo.

set /p "PHASE=Enter phase number [1 or 2]: "

if "%PHASE%"=="" (
    set "PHASE=2"
)

if not "%PHASE%"=="1" if not "%PHASE%"=="2" (
    echo.
    echo Error: Phase must be 1 or 2.
    echo.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo.
echo Running Sea++ compiler...
echo.

"%PYTHON_EXE%" -m run.main "%INPUT_FILE%" --phase %PHASE%

echo.
pause

endlocal
exit /b 0