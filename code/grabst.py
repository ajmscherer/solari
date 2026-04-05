from abc import ABC, abstractmethod
import re

BYTEPATTERN = '[0-9A-F][0-9A-F]'
COLORHEXAPATTERN = re.compile(f'#({BYTEPATTERN})({BYTEPATTERN})({BYTEPATTERN})')

class Color:
   
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        if len(args)==1:
            arg = args[0]
            if isinstance(arg, str):
                arg = arg.upper()
                match = COLORHEXAPATTERN.match(arg)
                if match:
                    r,g,b = match.groups()
                    self.R, self.G, self.B = [bytes.fromhex(v) for v in (r, g, b)]
                    return
        raise Exception(f"Unable to interpret {args} {kwargs}")
    
    def getRGB(self):
        return self.R, self.G, self.B

class Palette:
    BLACK = Color('#000000')
    WHITE = Color('#FFFFFF')
    RED = Color('#FF0000')

    @staticmethod
    def custom(*args, **kwargs):
        return Color(*args, **kwargs)

class Canvas(ABC):

    def drawLine(self, x0, y0, x1, y1, width=1, color=Palette.WHITE, opacity = 1.0):
        self._drawLine(x0, y0, x1,y1,width,color, opacity)

    def drawRectangle(self, x0, y0, x1, y1, width=1, color=Palette.WHITE, opacity = 1.0):
        self._drawLine(x0, y0, x1,y0,width,color, opacity)
        self._drawLine(x1, y0, x1,y1,width,color, opacity)
        self._drawLine(x1, y1, x0,y1,width,color, opacity)
        self._drawLine(x0, y1, x0,y0,width,color, opacity)

    def drawImage(self, image, x0=0, y0=0, rotation=0, verStretch=1.0, horStretch=1.0):
        self._drawImage(image=image,x0=x0, y0=y0, rotation=rotation, verStretch=verStretch, horStretch=horStretch)

    def getSize(self):
        '''Get width and heigh of the canvas area'''
        return self._getSize()

    # abstract method that need to be implemented


    @abstractmethod
    def _drawLine(self, x0, y0, x1, y1, width, color, opacity):
        pass
    @abstractmethod
    def _drawImage(self, image, x0, y0, rotation, verStretch, horStretch):
        '''Draw image'''

    @abstractmethod
    def _getSize(self):
        '''return (width,height)'''
        return 0.0,0.0
   

class CanvasRelative(Canvas):

    def __init__(self,baseCanvas:Canvas, xDelta=0.0, yDelta=0.0) -> None:
        super().__init__()
        self.baseCanvas = baseCanvas
        self.xDelta = xDelta
        self.yDelta = yDelta
        bw,bh = baseCanvas.getSize() # type: ignore
        self.size = bw-xDelta, bh -yDelta

    def _drawImage(self, image, x0, y0, rotation, verStretch, horStretch):
        xd , yd = self.xDelta, self.yDelta
        return self.baseCanvas.drawImage(image, x0+xd, y0+yd, rotation, verStretch, horStretch)

    def _drawLine(self, x0, y0, x1, y1, width, color, opacity):
        xd , yd = self.xDelta, self.yDelta
        return self.baseCanvas.drawLine(x0+xd, y0+yd, x1+xd, y1+yd, width, color, opacity)

    def _getSize(self):
        return self.size

class App(ABC):

    def __init__(self, framePerSecond, sizeRequirement) -> None:
        super().__init__()
        self.framePerSecond = framePerSecond
        self.sizeRequirement = sizeRequirement

    def drawMainWindow(self, canvas, time):
        self.draw(canvas=canvas, time=time)

    def run(self):
        self._run()

    @abstractmethod
    def _run(self):
        pass

    @abstractmethod
    def draw(self, canvas, time):
        pass

class Factory(ABC):

    APP = None

    @classmethod
    def getApp(cls):
        return cls.APP