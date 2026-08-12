# solari - a simple dashboard app with a Solari board style interface
# Copyright (C) 2024-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Volumio now-playing source for Tivoli mode. Polls the player REST API and
# formats the current track or station as a single live Solari message.
# Unlike news feeders, this does not rotate: the board holds one state and
# only flips when the formatted text changes.

from __future__ import annotations

import time
import textwrap
from datetime import datetime

import requests

from common import Helper, Message
from feeder import Feeder

logger = Helper.supplyLogger()

DEFAULT_VOLUMIO_HOST = '127.0.0.1'
DEFAULT_VOLUMIO_PORT = 3000
DEFAULT_POLL_SECONDS = 1.5
LIVE_DISPLAY_TIME = '1 hour'

# Tivoli 640x480 LCD. Equal inset on all sides so the board can be centered;
# 18 columns uses the leftover width that used to look like a fat left margin.
# Overscan is (left, bottom, right, top) in framebuffer pixels.
TIVOLI_DISPLAY_SIZE = (640, 480)
TIVOLI_OVERSCAN = (28, 28, 28, 28)
TIVOLI_PANEL_SIZE = (18, 7)
TIVOLI_GLYPH_PADDING = 2
TIVOLI_PANEL_PADDING = 4
TIVOLI_FPS = 12

def _tivoli_glyph_metrics():
    left, bottom, right, top = TIVOLI_OVERSCAN
    usable_w = TIVOLI_DISPLAY_SIZE[0] - left - right
    usable_h = TIVOLI_DISPLAY_SIZE[1] - top - bottom
    cols, rows = TIVOLI_PANEL_SIZE
    glyph_w = max(8, (usable_w - (cols - 1) * TIVOLI_GLYPH_PADDING - 2 * TIVOLI_PANEL_PADDING) // cols)
    glyph_h = max(12, (usable_h - (rows - 1) * TIVOLI_GLYPH_PADDING - 2 * TIVOLI_PANEL_PADDING) // rows)
    font = max(10, int(glyph_h * 0.70))
    return (glyph_w, glyph_h), font

TIVOLI_GLYPH_SIZE, TIVOLI_FONT_SIZE = _tivoli_glyph_metrics()

SERVICE_LABELS = {
    'webradio': 'RADIO',
    'mpd': 'LIBRARY',
    'spop': 'SPOTIFY',
    'airplay_emulation': 'AIRPLAY',
    'upnp': 'UPNP',
}

STATUS_LABELS = {
    'play': 'PLAY',
    'pause': 'PAUSE',
    'stop': 'STOP',
}


def _clean(value) -> str:
    if value is None:
        return ''
    text = str(value).strip()
    if text.lower() in ('null', 'none', 'undefined'):
        return ''
    return text


def _looks_like_stream_id(text: str) -> bool:
    """Drop artist/album fields that are really a stream filename or URL."""
    if not text:
        return False
    lowered = text.lower()
    if lowered.startswith('http://') or lowered.startswith('https://'):
        return True
    if ' ' not in text and '.' in text:
        return True
    return False


def _fit(text: str, width: int) -> str:
    return text[:width] if len(text) > width else text


def _header_line(now: datetime, col_width: int) -> str:
    hour = now.strftime(' %HH%M')
    options = [
        (f"{now.strftime('%a %b').upper()} {now.day} {now.year}", hour),
        (now.strftime('%Y-%m-%d').upper(), hour),
    ]
    day, clock = '', ''
    for option_day, option_hour in options:
        if len(option_day) + len(option_hour) <= col_width:
            day, clock = option_day, option_hour
            break
    return day + ' ' * (col_width - len(day) - len(clock)) + clock


def _compact_header(now: datetime, col_width: int) -> str:
    clock = now.strftime('%HH%M')
    date = f"{now.strftime('%b').upper()} {now.day}"
    if len(date) + len(clock) + 1 <= col_width:
        return date + ' ' * (col_width - len(date) - len(clock)) + clock
    return _fit(clock, col_width)


def _status_line(state: dict, service: str, col_width: int) -> str:
    status = STATUS_LABELS.get(_clean(state.get('status')).lower(), 'STOP')
    left = status
    volume = state.get('volume')
    if isinstance(volume, (int, float)) and not state.get('mute'):
        left = f"{status} {int(volume)}"
    right = service
    gap = col_width - len(left) - len(right)
    if gap < 1:
        return _fit(f"{left} {right}", col_width)
    return left + ' ' * gap + right


def format_volumio_state(state: dict, panel_size: tuple[int, int]) -> Message:
    """Turn a Volumio getState payload into a Solari message."""
    col_width, row_count = panel_size
    compact_header = col_width < 22
    compact_body = row_count <= 5
    compact = compact_body
    lines = [''] * row_count
    now = datetime.now().astimezone()
    lines[0] = _compact_header(now, col_width) if compact_header else _header_line(now, col_width)

    if state.get('_error'):
        host = _clean(state.get('_host'))
        reason = _clean(state.get('_reason')) or 'UNAVAILABLE'
        body = ['VOLUMIO', reason]
        if host:
            body.append(host)
        start = 1 if compact else 2
        for offset, item in enumerate(body):
            row = start + offset
            if row >= row_count - 1:
                break
            lines[row] = _fit(item, col_width)
        lines[-1] = _fit('ERROR', col_width)
        return Message('<br>'.join(lines), displayTime=LIVE_DISPLAY_TIME)

    title = _clean(state.get('title'))
    artist = _clean(state.get('artist'))
    album = _clean(state.get('album'))
    service_key = _clean(state.get('service')).lower()
    track_type = _clean(state.get('trackType')).upper()
    service = SERVICE_LABELS.get(service_key, track_type or service_key.upper() or 'VOLUMIO')

    if _looks_like_stream_id(artist):
        artist = ''
    if _looks_like_stream_id(album):
        album = ''

    if not title:
        title = 'NOTHING PLAYING' if _clean(state.get('status')).lower() == 'stop' else 'UNKNOWN'

    body_chunks = []
    for part in (title, artist, album if album != artist else ''):
        if part:
            body_chunks.extend(textwrap.wrap(part, width=col_width) or [part])

    start = 1 if compact else 2
    body_limit = row_count - 1
    for offset, item in enumerate(body_chunks):
        row = start + offset
        if row >= body_limit:
            break
        lines[row] = _fit(item, col_width)

    lines[-1] = _status_line(state, service, col_width)
    link = _clean(state.get('uri')) or None
    return Message('<br>'.join(lines), displayTime=LIVE_DISPLAY_TIME, link=link)


class FeederNowPlaying(Feeder):
    """Live Volumio feeder. getMessage() refreshes from the player; no rotation."""

    def __init__(
        self,
        host: str = DEFAULT_VOLUMIO_HOST,
        port: int = DEFAULT_VOLUMIO_PORT,
        panelSize: tuple[int, int] = TIVOLI_PANEL_SIZE,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.panelSize = panelSize
        self.poll_seconds = poll_seconds
        self.url = f'http://{host}:{port}/api/v1/getState'
        self._last_fetch = 0.0
        self._next_delay = poll_seconds
        self._refresh()

    def getMessage(self):
        self._maybe_refresh()
        return self._message

    def next(self):
        self._refresh()
        return self._message

    def _getNextMessage(self) -> Message:
        return self.getMessage()

    def _maybe_refresh(self):
        if time.time() - self._last_fetch < self._next_delay:
            return
        self._refresh()

    def _classify_error(self, exc: Exception) -> str:
        text = str(exc)
        if 'No route to host' in text or '[Errno 65]' in text:
            return 'NO ROUTE'
        if 'timed out' in text.lower() or 'timeout' in text.lower():
            return 'TIMEOUT'
        if 'Connection refused' in text:
            return 'REFUSED'
        return 'UNAVAILABLE'

    def _refresh(self):
        self._last_fetch = time.time()
        try:
            response = requests.get(self.url, timeout=3)
            response.raise_for_status()
            state = response.json()
            if not isinstance(state, dict):
                raise ValueError(f'unexpected getState payload: {type(state)!r}')
            self._next_delay = self.poll_seconds
        except Exception as exc:
            logger.warning(f'Volumio getState failed at {self.url}: {exc}')
            self._next_delay = min(self._next_delay * 2, 15.0)
            state = {
                '_error': str(exc),
                '_reason': self._classify_error(exc),
                '_host': f'{self.host}:{self.port}',
            }
        self._message = format_volumio_state(state, self.panelSize)


if __name__ == '__main__':
    samples = [
        {
            'status': 'play',
            'title': 'FIP',
            'artist': 'fip-hifi.aac',
            'album': None,
            'service': 'webradio',
            'trackType': 'webradio',
            'volume': 46,
            'uri': 'http://icecast.radiofrance.fr/fip-hifi.aac',
        },
        {
            'status': 'play',
            'title': 'Disconnection Notice',
            'artist': 'Sonic Youth',
            'album': 'Murray Street',
            'service': 'mpd',
            'trackType': 'song',
            'volume': 40,
            'uri': 'mnt/NAS/AlexCloud/Shared Music/Sonic Youth/Murray Street/02 Disconnection Notice.mp3',
        },
        {'_error': 'timed out', '_host': '192.168.1.4:3000'},
    ]
    for sample in samples:
        print('--- 30x7 ---')
        print(format_volumio_state(sample, (30, 7)).text.replace('<br>', '\n'))
        print('--- 16x7 ---')
        print(format_volumio_state(sample, TIVOLI_PANEL_SIZE).text.replace('<br>', '\n'))
