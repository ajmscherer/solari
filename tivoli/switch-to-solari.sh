#!/bin/bash
# Ask the Tivoli X session to show Solari (kills Chromium so the session loop continues).
echo solari > /home/volumio/.tivoli-display-mode
killall chromium-browser 2>/dev/null || true
killall chromium-browser-v7 2>/dev/null || true
exit 0
