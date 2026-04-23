#!/bin/bash
# Solari Launch Script - Mac / Linux / Raspberry Pi / ThinkPad

echo "🚀 Launching Solari split-flap board..."

# Activate virtual environment if it exists
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ virtual environment activated!"

# Run the app
python code/solari_run.py -fs

# Optional: keep the terminal open after exit (uncomment if you want)
# read -p "Press Enter to close..."