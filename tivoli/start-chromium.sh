#!/bin/bash
# Volumio Now Playing kiosk (port 4004). Used by tivoli-session.sh and by
# Solari when it prestarts Chromium so the tap handoff is not a black screen.
set -u
export DISPLAY="${DISPLAY:-:0}"
if pgrep -f 'chromium-browser.*volumiokiosk' >/dev/null 2>&1; then
  exit 0
fi
PREFS=/data/volumiokiosk/Default/Preferences
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "$PREFS" 2>/dev/null || true
sed -i 's/"exit_type":"Crashed"/"exit_type":"None"/' "$PREFS" 2>/dev/null || true
rm -f /data/volumiokiosk/SingletonCookie \
      /data/volumiokiosk/SingletonLock \
      /data/volumiokiosk/SingletonSocket 2>/dev/null || true

EXT=/home/volumio/solari/tivoli/kiosk-extension
LOAD_EXT=()
if [ -f "$EXT/manifest.json" ]; then
  LOAD_EXT=(--load-extension="$EXT" --disable-extensions-except="$EXT")
fi

exec /usr/bin/chromium-browser \
  --simulate-outdated-no-au='Tue, 31 Dec 2099 23:59:59 GMT' \
  --force-device-scale-factor=1 \
  "${LOAD_EXT[@]}" \
  --kiosk \
  --touch-events \
  --no-first-run \
  --noerrdialogs \
  --disable-infobars \
  --disable-gpu-compositing \
  --disable-3d-apis \
  --disable-breakpad \
  --disable-crash-reporter \
  --disable-background-networking \
  --disable-remote-extensions \
  --disable-pinch \
  --user-data-dir='/data/volumiokiosk' \
  http://localhost:4004
