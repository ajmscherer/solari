import datetime

from grkivy import KiviGraphicInterface
from grabst import GraphicApp, Palette
import math

from PIL import Image, ImageDraw, ImageFont

from enum import Enum, auto

class ic(Enum):
    '''image type'''
    WHOLE = auto()
    TOP = auto()
    BOTTOM = auto()

# DEFAULT_FONT_FILE_PATH = "/Users/alex/Downloads/freeroad/Freeroad Black.ttf"
DEFAULT_FONT_FILE_PATH = "././resources/Freeroad Regular.ttf"

class DemoApp(GraphicApp):

    def __init__(self, graphicInterface, framePerSecond, fontSize, fontFilePath) -> None:
        super().__init__(graphicInterface=graphicInterface,framePerSecond=framePerSecond, title="Demo App")
        #sizeRequirement = (800,300)
        sizeRequirement = None
        self.setSizeRequirement(sizeRequirement)
        self.imageCache = {}
        self.symbolHeight, self.symbolWidth = fontSize, fontSize
        self.font = ImageFont.truetype(fontFilePath,size=fontSize) 
        #self.buildImageCache('0123456789')
        pass


    def getN(self, time):
        d =(( ((time.toordinal()*24 + time.hour  * 60 ) + time.minute ) + time.second) % 60)  * 10 + time.microsecond // 100000
        return d

    def buildImageCache(self, symbols):
        for symbol in symbols:
            self.getImage(symbol)

    def getImage(self, symbol):

        if symbol not in self.imageCache:

            # retrieve width and height
            width, height = self.symbolWidth, self.symbolHeight

            # Create a new Image object with the desired dimensions
            transparent_color = (255, 255, 255, 50)
            font = self.font


            image = Image.new("RGBA", (width, height), transparent_color)

            # Create a drawing object to draw on the image
            draw = ImageDraw.Draw(image)

            # Draw a character at the center of the canvas
            mask = font.getmask(symbol)
            iWidth, iHeight = mask.size
            position = (width - iWidth) // 2, (height - iHeight) // 2

            draw.text(position, symbol, font=font)

            # flip image vertically
            image = image.transpose(Image.FLIP_TOP_BOTTOM) # type: ignore

            height_mid = height //2

            images = { 
                ic.WHOLE:image, 
                ic.TOP:image.crop((0,height_mid,width,height)),
                ic.BOTTOM:image.crop((0,0,width,height_mid)),
                }

            self.imageCache[symbol] = images

        result = self.imageCache[symbol]

        return result


    def drawCircle(self, canvas, time):
        
        xc, yc = [v/2.0 for v in canvas.getSize()]

        def coord(angle):
            x = xc + math.cos(angle) * xc * .9
            y = yc + math.sin(angle) * yc * .9
            return x,y

        angle0=math.pi/2.0
        x0 , y0 = coord(angle0)
        N = self.getN(time)
        for i in range(N):
            angle = angle0 - (i+1) / 600.0 *2 * math.pi
            x1 , y1 = coord(angle)
            canvas.drawLine(x0,y0, x1,y1, width=4, color=Palette.RED, opacity=0.4)
            x0,y0=x1,y1

    def drawRectangle(self, canvas, time:datetime.datetime):
        xc, yc = canvas.getSize()
        opacity=1
        f=min(xc ,yc) / 25
        canvas.drawRectangle(f,f,xc-f,yc-f, width=4, color=Palette.WHITE, opacity=opacity)

    def drawCounterImage(self, canvas, time):

        wc, hc = canvas.getSize()


        N = self.getN(time)
        string = f"{N:0>3}"
        string_length = len(string)
        padding =5
        x0=(wc-string_length * self.symbolWidth - (string_length-1) * padding) // 2
        y0=(hc - self.symbolHeight) //2

        ms = time.microsecond
        thr = 1e6 *.8
        vs = 1.0 if ms <thr else 1.0 - (ms-thr)/(1e6-thr)

        for symbol in string:
            image_full, image_top, image_bottom = self.getImage(symbol).values()
            canvas.drawImage(image_bottom, x0=x0, y0=y0, verStretch=1.0 )
            canvas.drawImage(image_top, x0=x0, y0=y0 + self.symbolHeight // 2 + padding,verStretch=vs)
            x0 += self.symbolWidth + padding


    def draw(self, canvas, time):
        self.drawCircle(canvas, time)
        if time.second % 2 == 0:
            self.drawRectangle(canvas,time)
        #self.drawCounterImage(canvas, time)

if __name__ == '__main__':
    gi = KiviGraphicInterface()
    app = DemoApp(graphicInterface=gi, framePerSecond=4, fontSize=250, fontFilePath=DEFAULT_FONT_FILE_PATH)
    app.run()