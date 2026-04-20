REM run.bat - Batch file to launch the Solari split-flap board application on Windows

@echo off
echo 🚀 Launching Solari split-flap board...

REM Activate virtual environment if it exists
if exist .venv (
  echo ✅ Activating virtual environment...
  call .venv\Scripts\activate.bat
) else (
  echo ⚠️  No .venv folder found. Running with system Python (make sure dependencies are installed).
)

REM Run the app
python code\solari_run.py

echo.
pause