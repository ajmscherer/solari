from feeder import FeederInfo
from infofetch import NewsFetcher_TASS
from grkivy import KiviGraphicInterface
from solari import DEFAULT_PANEL_SIZE, SolariApp


if __name__ == "__main__":
    
    # define GraphicInterface
    kiviInterface = KiviGraphicInterface()

    panelSize = DEFAULT_PANEL_SIZE

    # create fetcher
    fetcher = NewsFetcher_TASS()
    fetcher.start()

    feeder = FeederInfo(fetcher, colWidth=panelSize[0])
    
    # create the SolariApp
    solari = SolariApp(graphicInterface=kiviInterface,feeder=feeder, panelSize=panelSize)

    # run the app
    solari.run()