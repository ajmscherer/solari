from common import Helper
from infofetch import InfoSource
from feeder import FeederMix
from grkivy import KiviGraphicInterface
from solari import DEFAULT_PANEL_SIZE, SolariApp


# get Logger
logger = Helper.supplyLogger()
logger.info("Starting SolariApp...")
logger.debug(f"Available info sources: {[newsSource.name for newsSource in InfoSource]}")


# define GraphicInterface
kiviInterface = KiviGraphicInterface()

sources = [newsSource for newsSource in InfoSource if newsSource.name in [
    # 'DW',
    'ZEROHEDGE',
    # 'NHK_WORD',
    # 'GLOBO',
    # 'VATICAN_NEWS',
    # 'LA_CROIX',
    'NY_TIMES', 
    # 'CGTN', 
    'FRANCE_24', 
    # 'TIME_OF_INDIA', 
    # 'BBC', 
    # 'AL_JAZEERA', 
    # 'TASS', 
    # 'THE_GUARDIAN',
    # 'PR_NEWSWIRE',
    # 'AP_NEWS',
    # 'MOSCOW_TIME',
    ]]

# define panel size and feeder
panelSize = DEFAULT_PANEL_SIZE

feeder1 = FeederMix.buildFromInfoSource(sources, panelSize=panelSize)

feeder2 = FeederMix.buildFromInfoSource(InfoSource.XAI_NEWS_AGENT, panelSize=panelSize) # 15 minutes refresh interval

feeder = FeederMix([feeder1, feeder2])

# create the SolariApp
solari = SolariApp(graphicInterface=kiviInterface,feeder=feeder, panelSize=panelSize)

# run the app
solari.run()