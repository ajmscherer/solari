# Tivoli — Solari on the Volumio Raspberry Pi

This note is the install/update record for running Solari as the now-playing
display on the Tivoli player. **Update this file in git whenever the Pi setup
changes**, then copy it to the Pi (or just launch Solari — `run-tivoli.sh`
refreshes `/home/volumio/TIVOLI.md`).

| Copy | Path |
|---|---|
| Source of truth | this file, on branch `tivoli` |
| On the Pi (tree) | `/home/volumio/solari/TIVOLI.md` |
| On the Pi (home) | `/home/volumio/TIVOLI.md` |

Repo: https://github.com/ajmscherer/solari  
Branch: `tivoli`  
Mac checkout: `/Users/alex/Documents/CODE/PUBLISHED/solari`

Default `main` is the news board. Tivoli is **only** on when launched with the
`tivoli` argument.

```bash
python code/solari_run.py              # same as main
python code/solari_run.py tivoli       # Volumio now-playing
python code/solari_run.py tivoli -fs
```

<p align="center">
  <img src="resources/images/Volumio3.jpg" alt="Tivoli Model Two with Solari now-playing" width="680">
</p>

---

## What Tivoli is

- Hardware: Raspberry Pi 3 Model B Plus, Allo Boss / Innomaker I2S DAC, 640×480
  touchscreen (`wch.cn USB2IIC_CTP_CONTROL`)
- OS: Volumio 3.912 (Raspbian Buster, **Python 3.7.3**, armv7l)
- Player: hostname `tivoli`, LAN DHCP, user `volumio`
- Solari talks to Volumio at `http://127.0.0.1:3000/api/v1/getState`

Do **not** replace Volumio’s system Python. Do **not** run the Chromium kiosk
and Solari at the same time (869 MB RAM).

<p align="center">
  <img src="resources/images/Volumio2.jpg" alt="Tivoli stack on the shelf" width="680">
</p>

---

## Layout on disk (Pi)

```
/home/volumio/solari/           # application tree
  TIVOLI.md
  run-tivoli.sh                 # Pi launch (forces SDL2/X11)
  code/                         # Python sources
/home/volumio/.local/           # pip --user: Kivy 2.3.0, Pillow 9.x, schedule
/home/volumio/TIVOLI.md         # extra copy of this note
/opt/volumiokiosk.sh            # stock Volumio Now Playing kiosk (fallback)
```

There is no git checkout on the Pi unless you create one (see below). Historically
the tree was copied with `rsync`/`scp` from the Mac.

---

## Reinstall after a fresh Volumio image

### 1. Packages

```bash
sudo apt-get update
sudo apt-get install -y python3-pip \
  libsdl2-image-2.0-0 libsdl2-ttf-2.0-0 libsdl2-mixer-2.0-0
```

`libsdl2-2.0-0` is already on Volumio. pip may pull `build-essential`; that is OK.

### 2. Python deps (PiWheels, user install)

```bash
pip3 install --user --extra-index-url https://www.piwheels.org/simple \
  'Kivy==2.3.0' 'Pillow<10' 'requests<2.32' schedule
```

Kivy **2.3.1** has no cp37 armv7l wheel. Stay on **2.3.0**.  
Do not install `xai-sdk` or `simpleaudio` for Tivoli mode (lazy-imported).

### 3. Application code

From this Mac (after `git checkout tivoli`):

```bash
rsync -az --exclude '.venv' --exclude '.git' --exclude 'cache' --exclude 'logs' \
  --exclude '.zed' --exclude '__pycache__' \
  /Users/alex/Documents/CODE/PUBLISHED/solari/ \
  volumio@<tivoli-ip>:/home/volumio/solari/
```

Or on the Pi, clone the branch:

```bash
git clone -b tivoli https://github.com/ajmscherer/solari.git /home/volumio/solari
```

```bash
chmod +x /home/volumio/solari/run-tivoli.sh
cp /home/volumio/solari/TIVOLI.md /home/volumio/TIVOLI.md
```

### 4. Take the screen (stop the kiosk)

The Touch Display plugin starts Chromium via `/opt/volumiokiosk.sh`. Solari needs
that X session **or** its own `startx`.

```bash
# stop Chromium kiosk (comes back on a Volumio reboot unless you change boot)
pkill -f /opt/volumiokiosk.sh || true
killall chromium-browser 2>/dev/null || true
killall Xorg 2>/dev/null || true
sleep 2

setsid startx /home/volumio/solari/run-tivoli.sh -fs -- :0 -nocursor \
  </dev/null >/tmp/solari-x.log 2>&1 &
```

`run-tivoli.sh` sets `KIVY_WINDOW=sdl2`, `KIVY_GL_BACKEND=sdl2`,
`KIVY_BCM_DISPMANX=0`. Without those, Kivy uses `egl_rpi` and dies on `/dev/vchiq`.

### 5. Restore stock Now Playing

```bash
killall python3 2>/dev/null || true
killall Xorg 2>/dev/null || true
sleep 2
setsid startx /opt/volumiokiosk.sh -- :0 -nocursor </dev/null &
```

A reboot also returns the Volumio kiosk unless you add a boot service.

---

## How the Pi tree gets updated

1. Change code on the Mac, on branch `tivoli`.
2. Commit / push to GitHub.
3. Copy to the Pi (`rsync` as above, or `git pull` if you cloned).
4. Restart Solari (`/tmp/restart-tivoli-display.sh` if present, or the
   `startx … run-tivoli.sh` block).
5. If this note changed, edit **this file in git** first. The next Solari start
   copies it to `/home/volumio/TIVOLI.md`.

The Pi does **not** pull GitHub by itself.

---

## Switching displays

| From | To | Action |
|---|---|---|
| Solari | Volumio | Tap the screen (or press `v` on a keyboard) |
| Volumio | Solari | Gold **SOLARI** tab on the left of the Now Playing screen. Also Browse → **Solari** tile (music-note icon in Now Playing, or Sources in the main UI) |
| Boot / reboot | Solari | Default. `volumio-kiosk.service` starts `tivoli/tivoli-session.sh` |

The Volumio kiosk is the Now Playing plugin (`http://localhost:4004`), not the main Browse home. A missing **Solari** tile usually means the `solari_display` plugin failed to start (`kew` module path). Re-run `tivoli/install-display.sh` then `volumio vrestart`.

The Now Playing “info” view asks for a Genius lyrics token. We do not ship a token. The kiosk hides that error; lyrics stay off unless you add your own token in the Now Playing plugin settings.

Mode is stored in `/home/volumio/.tivoli-display-mode` (`solari` or `volumio`).
Scripts: `tivoli/switch-to-solari.sh`, `tivoli/switch-to-volumio.sh`.

One-time install (after the files are on the Pi):

```bash
bash /home/volumio/solari/tivoli/install-display.sh
echo volumio | sudo -S systemctl restart volumio-kiosk.service
volumio vrestart
```

That writes a systemd drop-in so a reboot comes up on Solari, and registers the
Browse tile. Leave the Touch Display plugin enabled (it owns the kiosk unit).

---

## Display calibration (current)

<p align="center">
  <img src="resources/images/Volumio1.jpg" alt="Calibrated 18x7 board on the 640x480 LCD" height="340">
  &nbsp;&nbsp;
  <img src="resources/images/volumio-demo.gif" alt="Flap animation on Tivoli" height="340">
</p>

Framebuffer is **640×480** (confirmed via `fb0` and `xrandr`).  
Tivoli mode forces that size in Kivy **before** the window is created.

| Setting | Value |
|---|---|
| Panel | 18 columns × 7 rows |
| Overscan (L,B,R,T) | 28, 28, 28, 28 (equal; board is then centered) |
| Frame rate | 6 |
| Glyph size | computed from the usable 584×424 rectangle |

Constants live in `code/volumio.py` (`TIVOLI_*`). Layout is a compact now-playing
card (date/time, title/artist/album, `PLAY 46` / source).

Graphics are Mesa **llvmpipe** (CPU). Fine for 18×7 at 6 fps with cached
textures. Do not let `simpleaudio` open the Boss DAC.

---

## Mac-side check (no Pi display)

```bash
cd /Users/alex/Documents/CODE/PUBLISHED/solari
source .venv/bin/activate
python code/solari_run.py tivoli --host <tivoli-ip>
```

If that fails with `NO ROUTE` from the IDE, allow **Local Network** for Python
in macOS Privacy settings. Terminal usually already has permission.

VS Code launch item (local `.vscode/launch.json`, gitignored):
**Tivoli (Volumio now-playing)** → `tivoli --host <tivoli-ip>`.

---

## Machine manifest (discovered 2026-08-12)

No passwords, tokens, Wi‑Fi PSKs, or API keys are recorded here. Treat the
`volumio` login as sensitive and change it if it is still the factory default.

### Identity

| | |
|---|---|
| Player name | Tivoli |
| Hostname | `tivoli` |
| Typical LAN address | DHCP on `wlan0` |
| SSH | user `volumio`, port 22 (key login was not set up) |
| Timezone | America/New_York |
| UI language | English |

### Hardware

| | |
|---|---|
| Board | Raspberry Pi 3 Model B Plus Rev 1.4 |
| CPU | 4× ARM Cortex-A53, armv7l, 600–1400 MHz |
| RAM | 869 MiB (no swap) |
| Storage | 32 GB microSD (`mmcblk0`) |
| Ethernet | `eth0` present, usually unplugged (no carrier) |
| Wi‑Fi | `wlan0`, DHCP client |
| Display | 640×480 framebuffer (`BCM2708 FB` / X `640x480`) |
| Touch | USB HID `wch.cn USB2IIC_CTP_CONTROL` (QinHeng `1a86:e5e3`) |
| DAC | I2S HAT, ALSA card `BossDAC` / pcm512x, overlay `allo-boss-dac-pcm512x-audio`, labelled **Innomaker DAC** in Volumio |
| Other audio | onboard HDMI and headphone jack present, idle |
| USB | Pi hub (SMSC 0424) plus the touch controller |

### Disk layout

| Device | Label | Size | Mount |
|---|---|---|---|
| `mmcblk0p1` | boot (vfat) | 91.6 MB | `/boot` |
| `mmcblk0p2` | volumio (ext4) | 2.5 GB | `/imgpart` |
| `mmcblk0p3` | volumio_data (ext4) | 27.1 GB | overlay upper (`/mnt/ext`) |
| loop squashfs | | ~498 MB | `/static` (read-only OS) |
| overlay | | ~27 GB | `/` (~24 GB free at discovery) |

### Operating system

| | |
|---|---|
| Product | Volumio 3.912 for Raspberry Pi |
| Base | Raspbian GNU/Linux 10 (buster), Debian 10.13 |
| Kernel | `6.6.62-v7+` `#1816` armv7l |
| Build date | Fri 27 Feb 2026 |
| Python | **3.7.3** (`/usr/bin/python3`) — do not replace |
| Auto-update | off |
| Accounts | `root`, `volumio` (uid 1000, groups include `audio`, `gpio`, `i2c`, `spi`) |

### Audio / player stack

- Output device: BossDAC, hardware mixer `Digital`, no resampling
- Observed playback: 48 kHz / 32-bit stereo
- MPD on `localhost:6600` (library last scanned 2025-09-20: ~1447 artists / 1049 albums / 17400 tracks)
- Webradio (FIP and a Radio France–heavy favourite list)
- Spotify Connect: `spop` + `go-librespot` (account linked; tokens not stored here)
- AirPlay: `shairport-sync`
- UPnP renderer: `upmpdcli`
- MyVolumio: signed in (tokens not stored here)

Volumio webradio `getState` for FIP typically only reports `title=FIP` and
`artist=fip-hifi.aac` — no current track. Library and AirPlay do send title/artist.

### Network services (listening)

| Port | Role |
|---|---|
| 22 | SSH |
| 139 / 445 | Samba (shares: Internal Storage, USB, NAS; guest write was enabled) |
| 3000 / 3005 | Volumio UI |
| 3001 | albumart |
| 4004 | Now Playing kiosk page |
| 5000 / 49149 / 49152 | UPnP |
| 6600 | MPD |
| 9879 | Spotify Connect (localhost) |

NAS mount configured: CIFS share **AlexCloud** (`Public`, SMB 2.1, guest). Often not mounted. USB `/media` was empty.

UPnP favourite seen toward a LAN media server on port 9000 (Twonky-style).

### Volumio plugins (user-installed)

| Plugin | Category | Notes |
|---|---|---|
| `spop` | music_service | Spotify, started |
| `podcast` | music_service | installed, stopped |
| `now_playing` | user_interface | kiosk UI on :4004 |
| `touch_display` | user_interface | owns `volumio-kiosk.service` / X |
| `Systeminfo` | user_interface | started |
| `solari_display` | music_service | Browse tile → switch to Solari |

Hotspot name seen in config: `Volumio-201DF` (not used while associated to LAN).

### Solari-on-Pi extras (not stock Volumio)

- App tree `/home/volumio/solari`
- pip `--user`: Kivy **2.3.0**, Pillow 9.x, `schedule`
- apt: `python3-pip`, `libsdl2-image/ttf/mixer` (plus build-essential pulled in)
- systemd drop-in: `/etc/systemd/system/volumio-kiosk.service.d/tivoli.conf`
- Display mode file: `/home/volumio/.tivoli-display-mode`

### Full-card backup (Mac)

A live gzip image of the 32 GB card (taken 2026-08-12, playback paused) is on this Mac:

`/Users/alex/Backups/tivoli/tivoli-sdcard-20260812.img.gz`

Restore steps are in `RESTORE.txt` next to it. That image predates Solari-on-Pi.

---

## When you change Solari-for-Pi

Update **this file in the same PR/commit** (packages, paths, overscan, launch,
and this manifest if hardware or services change). Then deploy so both Pi
copies stay current.
