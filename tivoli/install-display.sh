#!/bin/bash
# Install Tivoli display switching: boot into Solari, tap to Volumio,
# Browse → Solari tile to come back.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_SRC="$ROOT/tivoli/volumio-plugin"
PLUGIN_DST=/data/plugins/music_service/solari_display
SUDO="sudo -n"
if ! $SUDO true 2>/dev/null; then
  SUDO="sudo"
fi

chmod +x "$ROOT/run-tivoli.sh" \
  "$ROOT/tivoli/tivoli-session.sh" \
  "$ROOT/tivoli/switch-to-solari.sh" \
  "$ROOT/tivoli/switch-to-volumio.sh"

echo "Installing Volumio plugin to $PLUGIN_DST"
mkdir -p "$PLUGIN_DST"
cp -a "$PLUGIN_SRC/." "$PLUGIN_DST/"
chown -R volumio:volumio "$PLUGIN_DST"

python3 - << 'PY'
import json
from pathlib import Path
p = Path('/data/configuration/plugins.json')
data = json.loads(p.read_text())
ms = data.setdefault('music_service', {})
ms['solari_display'] = {
    'enabled': {'type': 'boolean', 'value': True},
    'status': {'type': 'string', 'value': 'STARTED'},
}
p.write_text(json.dumps(data, indent=2) + '\n')
print('registered solari_display in', p)
PY

echo "Pointing volumio-kiosk.service at tivoli-session.sh"
$SUDO mkdir -p /etc/systemd/system/volumio-kiosk.service.d
$SUDO tee /etc/systemd/system/volumio-kiosk.service.d/tivoli.conf >/dev/null << EOF
[Service]
ExecStart=
ExecStart=/usr/bin/startx /etc/X11/Xsession $ROOT/tivoli/tivoli-session.sh -- -nocursor
EOF

echo solari > /home/volumio/.tivoli-display-mode
chown volumio:volumio /home/volumio/.tivoli-display-mode
chmod 664 /home/volumio/.tivoli-display-mode
cp -f "$ROOT/TIVOLI.md" /home/volumio/TIVOLI.md 2>/dev/null || true
chown volumio:volumio /home/volumio/TIVOLI.md 2>/dev/null || true

$SUDO systemctl daemon-reload
$SUDO systemctl enable volumio-kiosk.service
echo "Restart Volumio to load the Solari browse tile, then restart the kiosk:"
echo "  volumio vrestart"
echo "  sudo systemctl restart volumio-kiosk.service"
