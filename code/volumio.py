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

import time
from datetime import datetime

import requests

from common import Helper, Message
from feeder import Feeder

logger = Helper.supplyLogger()

DEFAULT_VOLUMIO_HOST = '127.0.0.1'
DEFAULT_VOLUMIO_PORT = 3000
DEFAULT_POLL_SECONDS = 1.5
LIVE_DISPLAY_TIME = '1 hour'

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


def format_volumio_state(state: dict, panel_size: tuple[int, int]) -> Message:
    """Turn a Volumio getState payload into a 30x7-style Solari message."""
    col_width, row_count = panel_size
    lines = [''] * row_count

    now = datetime.now().astimezone()
    lines[0] = _header_line(now, col_width)

    if state.get('_error'):
        host = _clean(state.get('_host'))
        if row_count > 2:
            lines[2] = _fit('VOLUMIO', col_width)
        if row_count > 3:
            lines[3] = _fit('UNAVAILABLE', col_width)
        if row_count > 4 and host:
            lines[4] = _fit(host, col_width)
        if row_count > 0:
            lines[-1] = _fit('ERROR', col_width)
        return Message('<br>'.join(lines), displayTime=LIVE_DISPLAY_TIME)

    title = _clean(state.get('title'))
    artist = _clean(state.get('artist'))
    album = _clean(state.get('album'))
    status = STATUS_LABELS.get(_clean(state.get('status')).lower(), 'STOP')
    service_key = _clean(state.get('service')).lower()
    track_type = _clean(state.get('trackType')).upper()
    service = SERVICE_LABELS.get(service_key, track_type or service_key.upper() or 'VOLUMIO')

    if _looks_like_stream_id(artist):
        artist = ''
    if _looks_like_stream_id(album):
        album = ''

    if not title:
        title = 'NOTHING PLAYING' if status == 'STOP' else 'UNKNOWN'

    body = [title]
    if artist:
        body.append(artist)
    if album and album != artist:
        body.append(album)

    # Date on row 0, blank row 1, then title / artist / album.
    body_row = 2
    for item in body:
        if body_row >= row_count - 1:
            break
        lines[body_row] = _fit(item, col_width)
        body_row += 1

    volume = state.get('volume')
    left = status
    if isinstance(volume, (int, float)) and not state.get('mute'):
        left = f"{status} {int(volume)}"

    right = service
    gap = col_width - len(left) - len(right)
    if gap < 1:
        lines[-1] = _fit(f"{left} {right}", col_width)
    else:
        lines[-1] = left + ' ' * gap + right

    link = _clean(state.get('uri')) or None
    return Message('<br>'.join(lines), displayTime=LIVE_DISPLAY_TIME, link=link)


class FeederNowPlaying(Feeder):
    """Live Volumio feeder. getMessage() refreshes from the player; no rotation."""

    def __init__(
        self,
        host: str = DEFAULT_VOLUMIO_HOST,
        port: int = DEFAULT_VOLUMIO_PORT,
        panelSize: tuple[int, int] = (30, 7),
        poll_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.panelSize = panelSize
        self.poll_seconds = poll_seconds
        self.url = f'http://{host}:{port}/api/v1/getState'
        self._last_fetch = 0.0
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
        if time.time() - self._last_fetch < self.poll_seconds:
            return
        self._refresh()

    def _refresh(self):
        self._last_fetch = time.time()
        try:
            response = requests.get(self.url, timeout=2)
            response.raise_for_status()
            state = response.json()
            if not isinstance(state, dict):
                raise ValueError(f'unexpected getState payload: {type(state)!r}')
        except Exception as exc:
            logger.warning(f'Volumio getState failed at {self.url}: {exc}')
            state = {'_error': str(exc), '_host': f'{self.host}:{self.port}'}
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
        message = format_volumio_state(sample, (30, 7))
        print('---')
        print(message.text.replace('<br>', '\n'))
