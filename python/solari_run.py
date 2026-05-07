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


# parse command-line arguments
parser = argparse.ArgumentParser(description='Solari split-flap board')
parser.add_argument('-fs', '--fullscreen', action='store_true', help='Start in fullscreen mode')
args = parser.parse_args()


# get Logger
logger = Helper.supplyLogger()
logger.info("Starting SolariApp...")
logger.debug(f"Available info sources: {[newsSource.name for newsSource in InfoSource]}")


# define GraphicInterface
kiviInterface = KiviGraphicInterface()

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

# define panel size and feeder
panelSize = DEFAULT_PANEL_SIZE

feeder1 = FeederMix.buildFromInfoSource(sources, panelSize=panelSize)

feeder2 = FeederMix.buildFromInfoSource(InfoSource.XAI_NEWS_AGENT, panelSize=panelSize) # 15 minutes refresh interval

feeder = FeederMix([feeder1, feeder2])

# create the SolariApp
solari = SolariApp(graphicInterface=kiviInterface, feeder=feeder, panelSize=panelSize)

# run the app
solari.run(fullscreen=args.fullscreen)