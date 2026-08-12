#!/bin/bash
# Launch Solari in Tivoli (Volumio now-playing) mode.
# On the Pi this must use SDL2/X11, not the legacy egl_rpi backend.

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Keep a home-directory copy of the Pi install note next to this tree.
if [ -f "$ROOT/TIVOLI.md" ] && [ -d /home/volumio ]; then
  cp -f "$ROOT/TIVOLI.md" /home/volumio/TIVOLI.md
fi

if [ -f .venv/bin/activate ]; then
  # Desktop / Mac
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec python code/solari_run.py tivoli "$@"
fi

export DISPLAY="${DISPLAY:-:0}"
export KIVY_WINDOW=sdl2
export KIVY_GL_BACKEND=sdl2
export KIVY_BCM_DISPMANX=0
export KIVY_NO_ARGS=1
exec python3 "$ROOT/code/solari_run.py" tivoli "$@"
