#!/bin/bash
# Solari Launch Script - Mac / Linux / Raspberry Pi / ThinkPad

echo "🚀 Launching Solari split-flap board..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
  echo "✅ Activating virtual environment..."
  source .venv/bin/activate
else
  echo "⚠️  No .venv folder found. Running with system Python (make sure dependencies are installed)."
fi

# Run the app
python code/solari_run.py

# Optional: keep the terminal open after exit (uncomment if you want)
# read -p "Press Enter to close..."