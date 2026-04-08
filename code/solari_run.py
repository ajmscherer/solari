from feeder import Feeder
from grkivy import KiviGraphicInterface
from solari import DEFAULT_PANEL_SIZE, SolariApp


if __name__ == "__main__":
    
    # define GraphicInterface
    kiviInterface = KiviGraphicInterface()

    panelSize = DEFAULT_PANEL_SIZE
    charmap = Feeder.charmap(panelSize=panelSize)

    # create the SolariApp
    solari = SolariApp(graphicInterface=kiviInterface,feeder=Feeder.charmap(panelSize=panelSize), panelSize=panelSize)

    # run the app
    solari.run()