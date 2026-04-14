from infofetch import NewsSource
from feeder import FeederMix
from grkivy import KiviGraphicInterface
from solari import DEFAULT_PANEL_SIZE, SolariApp


if __name__ == "__main__":
    
    # define GraphicInterface
    kiviInterface = KiviGraphicInterface()

    sources = [newsSource for newsSource in NewsSource if newsSource.name in [
        'DW',
        # 'ZEROHEDGE',
        # 'NHK_WORD',
        # 'GLOBO',
        'VATICAN_NEWS',
        # 'LA_CROIX',
        # 'NY_TIMES', 
        # 'CGTN', 
        # 'FRANCE_24', 
        # 'TIME_OF_INDIA', 
        # 'BBC', 
        # 'AL_JAZEERA', 
        # 'TASS', 
        # 'THE_GUARDIAN',
        ]]

    # define panel size and feeder
    panelSize = DEFAULT_PANEL_SIZE
    feeder = FeederMix.buildFromNewsSource(sources, panelSize=panelSize)
    
    # create the SolariApp
    solari = SolariApp(graphicInterface=kiviInterface,feeder=feeder, panelSize=panelSize)

    # run the app
    solari.run()