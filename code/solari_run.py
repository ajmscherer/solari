from feeder import FeederMix
from grkivy import KiviGraphicInterface
from solari import DEFAULT_PANEL_SIZE, SolariApp


if __name__ == "__main__":
    
    # define GraphicInterface
    kiviInterface = KiviGraphicInterface()

    # define panel size and feeder
    panelSize = DEFAULT_PANEL_SIZE
    feeder = FeederMix.buildFromNewsSource("BBC,FRANCE24,ALJAZEERA,TASS", colWidth=panelSize[0])
    
    # create the SolariApp
    solari = SolariApp(graphicInterface=kiviInterface,feeder=feeder, panelSize=panelSize)

    # run the app
    solari.run()