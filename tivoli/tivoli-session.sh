#!/bin/bash
# X session for Tivoli: Solari by default, Volumio kiosk on request.
# Started by volumio-kiosk.service (systemd drop-in).
# Exit 10 from Solari (screen tap or 'v') switches to Volumio.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE_FILE=/home/volumio/.tivoli-display-mode
LOG=/tmp/tivoli-session.log

log() { echo "$(date -Iseconds) $*" >> "$LOG"; }

if [ -f "$ROOT/TIVOLI.md" ]; then
  cp -f "$ROOT/TIVOLI.md" /home/volumio/TIVOLI.md 2>/dev/null || true
fi

if [ ! -f "$MODE_FILE" ]; then
  echo solari > "$MODE_FILE"
fi

log "waiting for Volumio on :3000"
for _ in $(seq 1 60); do
  if timeout 1 bash -c '</dev/tcp/127.0.0.1/3000' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if [ -x /usr/bin/openbox-session ]; then
  openbox-session >/tmp/tivoli-openbox.log 2>&1 &
fi

log "session loop starting"
while true; do
  MODE="$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null || true)"
  [ -n "$MODE" ] || MODE=solari
  log "mode=$MODE"
  if [ "$MODE" = volumio ]; then
    sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' /data/volumiokiosk/Default/Preferences 2>/dev/null || true
    sed -i 's/"exit_type":"Crashed"/"exit_type":"None"/' /data/volumiokiosk/Default/Preferences 2>/dev/null || true
    rm -f /data/volumiokiosk/SingletonCookie /data/volumiokiosk/SingletonLock /data/volumiokiosk/SingletonSocket 2>/dev/null || true
    export DISPLAY="${DISPLAY:-:0}"
    /usr/bin/chromium-browser \
      --simulate-outdated-no-au='Tue, 31 Dec 2099 23:59:59 GMT' \
      --force-device-scale-factor=1 \
      --load-extension= \
      --kiosk \
      --touch-events \
      --no-first-run \
      --noerrdialogs \
      --disable-gpu-compositing \
      --disable-3d-apis \
      --disable-breakpad \
      --disable-crash-reporter \
      --disable-background-networking \
      --disable-remote-extensions \
      --disable-pinch \
      --user-data-dir='/data/volumiokiosk' \
      http://localhost:4004
    log "chromium exited $?"
  else
    "$ROOT/run-tivoli.sh" -fs
    code=$?
    now="$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null || true)"
    log "solari exited $code file=$now"
    if [ "$code" -eq 10 ] || [ "$now" = volumio ]; then
      printf '%s\n' volumio > "$MODE_FILE"
      log "next mode=volumio"
    fi
  fi
  sleep 0.4
done
