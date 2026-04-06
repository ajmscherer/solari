from grkivy import KiviGraphicInterface
from solari import SolariApp


if __name__ == "__main__":
    
    # define GraphicInterface
    kiviInterface = KiviGraphicInterface()

    # create the SolariApp
    solari = SolariApp(graphicInterface=kiviInterface)

    # run the app
    solari.run()