#!/bin/bash
# X session for Tivoli: Solari by default, Volumio kiosk on request.
# Started by volumio-kiosk.service (systemd drop-in).
# Exit 10 from Solari (screen tap or 'v') switches to Volumio.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE_FILE=/home/volumio/.tivoli-display-mode
LOG=/tmp/tivoli-session.log

log() { echo "$(date -Iseconds) $*" >> "$LOG"; }

ensure_switchd() {
  if ! timeout 0.3 bash -c '</dev/tcp/127.0.0.1/4011' >/dev/null 2>&1; then
    python3 "$ROOT/tivoli/switchd.py" >>/tmp/tivoli-switchd.log 2>&1 &
    log "started switchd pid=$!"
  fi
}

chromium_running() {
  pgrep -f 'chromium-browser.*volumiokiosk' >/dev/null 2>&1
}

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

ensure_switchd
xsetroot -solid '#000000' 2>/dev/null || true

log "session loop starting"
while true; do
  MODE="$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null || true)"
  [ -n "$MODE" ] || MODE=solari
  log "mode=$MODE"
  if [ "$MODE" = volumio ]; then
    ensure_switchd
    xsetroot -solid '#000000' 2>/dev/null || true
    export DISPLAY="${DISPLAY:-:0}"
    for _ in 1 2 3 4 5 6 7 8; do
      chromium_running && break
      sleep 0.2
    done
    if chromium_running; then
      log "chromium already running"
      while chromium_running; do
        sleep 0.4
      done
      log "chromium exited"
    else
      "$ROOT/tivoli/start-chromium.sh"
      log "chromium exited $?"
    fi
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
  sleep 0.05
done
