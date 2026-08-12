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

# This module defines the main entry point for the SolariApp. It sets up the 
# graphic interface, the feeder, and runs the app.

import argparse

from common import Helper
from infofetch import InfoSource
from feeder import FeederMix
from grkivy import KiviGraphicInterface
from solari import DEFAULT_PANEL_SIZE, SolariApp
from volumio import DEFAULT_VOLUMIO_HOST, DEFAULT_VOLUMIO_PORT, FeederNowPlaying


# parse command-line arguments
parser = argparse.ArgumentParser(description='Solari split-flap board')
parser.add_argument(
    'mode',
    nargs='?',
    default=None,
    metavar='MODE',
    help='Use "tivoli" to show Volumio now-playing. Omit for the default news board.',
)
parser.add_argument(
    '--host',
    default=DEFAULT_VOLUMIO_HOST,
    help='Volumio host in tivoli mode (default: 127.0.0.1)',
)
parser.add_argument(
    '--port',
    type=int,
    default=DEFAULT_VOLUMIO_PORT,
    help='Volumio port in tivoli mode (default: 3000)',
)
parser.add_argument('-fs', '--fullscreen', action='store_true', help='Start in fullscreen mode')
args = parser.parse_args()
if args.mode not in (None, 'tivoli'):
    parser.error(f'unknown mode {args.mode!r}; use "tivoli" or omit for the default news board')


# get Logger
logger = Helper.supplyLogger()
logger.info("Starting SolariApp...")
logger.debug(f"Available info sources: {[newsSource.name for newsSource in InfoSource]}")


# define GraphicInterface
kiviInterface = KiviGraphicInterface()

# define panel size and feeder
panelSize = DEFAULT_PANEL_SIZE

if args.mode == 'tivoli':
    logger.info(f"Tivoli mode: Volumio now-playing at {args.host}:{args.port}")
    feeder = FeederNowPlaying(host=args.host, port=args.port, panelSize=panelSize)
else:
    sources = [newsSource for newsSource in InfoSource if newsSource.name in [
        'DW',
        'ZEROHEDGE',
        'NHK_WORD',
        # 'GLOBO',
        'VATICAN_NEWS',
        # 'LA_CROIX',
        'NY_TIMES',
        'CGTN',
        'FRANCE_24',
        'TIME_OF_INDIA',
        'BBC',
        'AL_JAZEERA',
        'TASS',
        'THE_GUARDIAN',
        'PR_NEWSWIRE',
        'AP_NEWS',
        # 'MOSCOW_TIME',
        ]]

    feeder1 = FeederMix.buildFromInfoSource(sources, panelSize=panelSize)

    feeder2 = FeederMix.buildFromInfoSource(InfoSource.XAI_NEWS_AGENT, panelSize=panelSize) # 15 minutes refresh interval

    feeder = FeederMix([feeder1, feeder2])

# create the SolariApp
solari = SolariApp(graphicInterface=kiviInterface, feeder=feeder, panelSize=panelSize)

# run the app
solari.run(fullscreen=args.fullscreen)