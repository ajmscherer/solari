#!/bin/bash
# Ask the Tivoli X session to show Volumio (Solari tap already does this via exit 10).
echo volumio > /home/volumio/.tivoli-display-mode
# If Solari is in the foreground, stop it so the session loop can start Chromium.
for pid in $(ps -eo pid,args | awk '/solari_run.py/ && !/awk/ {print $1}'); do
  kill "$pid" 2>/dev/null || true
done
exit 0
