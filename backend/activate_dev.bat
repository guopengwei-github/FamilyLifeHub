@echo off
REM ABOUTME: Activates main worktree venv and sets PYTHONPATH for current worktree

REM Get current directory (should be .../backend)
set CURRENT_DIR=%cd%

REM Copy .env from main worktree if not exists
if not exist "%CURRENT_DIR%\.env" (
    echo Copying .env from main worktree...
    copy D:\ai\family_life_hub\backend\.env "%CURRENT_DIR%\.env" >nul
)

echo Activating virtual environment from main worktree...
call D:\ai\family_life_hub\backend\venv\Scripts\activate.bat

echo Setting PYTHONPATH to current worktree...
set PYTHONPATH=%CURRENT_DIR%

echo.
echo Environment ready:
echo - Virtual env: D:\ai\family_life_hub\backend\venv
echo - PYTHONPATH: %PYTHONPATH%
echo - Python version:
python --version
echo.
echo You can now run: python main.py
cmd.exe /k
