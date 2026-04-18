'''
Code that simulates a Split-Flap or Solari board

A Scherer
2024 

'''

import unicodedata

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

import simpleaudio
import threading
import random
import time

from grabst import CanvasRelative, GraphicApp, Palette

import datetime
from abc import ABC, abstractmethod
from enum import Enum, auto
import math
import webbrowser

from feeder import Feeder

from common import RESOURCES_DIR, Helper


logger = Helper.supplyLogger()


# Definition of constants


DEFAULT_ROTATION_SPEED = 125  # time in milliseconds to go from one charactere to the next
DEFAULT_FRAME_PER_SECOND = 24

DEFAULT_GLYPH_SIZE = 35, 60,
GLYPH_PADDING = 6
DEFAULT_FONT_SIZE = 42

DEFAULT_PANEL_SIZE = 30 , 7
DEFAULT_PANEL_PADDING = 50
DEFAULT_PORT_REFRESH_LAPSE = 10 # time in milliseconds for the panel to deal with one port to the next when refreshing 
DEFAULT_SOUND = False

#all_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!#$%&*()-=+;:\",<.>/?_ "
ALPHA_CHAR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALL_CHARS = " 01234567890"+ALPHA_CHAR+"!'\"$%&*-=+:;,.?/_#"


#DEFAULT_FONT_FILE_PATH = "graphics/Solari.ttf"
EXCEPTION_NOT_IMPLEMENTED = 'Not implemented yet'

DEFAULT_FONT_FILE_PATH = RESOURCES_DIR / "Freeroad Regular.ttf"
RELAY_SOUND_PATH = RESOURCES_DIR / "relay_sound.wav"


# enumerations

class ic(Enum):
    '''image type'''
    WHOLE = auto()
    TOP = auto()
    BOTTOM = auto()


class sq(Enum):
    '''Square Enumeration'''
    RED_SQUARE = Palette.RED
    WHIE_SQUARE = Palette.WHITE


# class definition

class myobject:
    pass

class Glyph(myobject, ABC):
    ''' A Glyph is a symbol that can be displayed on the panel. It can be a character, a number, a symbol, etc. It is defined by its size and the images to display for each half of the panel (top and bottom). The images are built on demand and cached for future use. The images are built by the buildImages method that need to be implemented by the subclass. The getImages method returns the images to display for each half of the panel. The images are stored in a dictionary with the keys being the image type (whole, top, bottom) and the values being the images to display for each half of the panel. The whole image is used when the panel is not rotating, the top and bottom images are used when the panel is rotating.'''

    def __init__(self, size) -> None:
        '''size is a tuple (width, height) that defines the size of the glyph. The size of the panel is defined by the size of the glyph and the padding between the glyphs.'''
        super().__init__()
        self.cacheImage = None
        self.size = size

    def getImages(self):
        '''Get the images to display for each half of the panel. The images are stored in a dictionary with the keys being the image type (whole, top, bottom) and the values being the images to display for each half of the panel. The whole image is used when the panel is not rotating, the top and bottom images are used when the panel is rotating. The images are built on demand and cached for future use. The images are built by the buildImages method that need to be implemented by the subclass.'''
        if not self.cacheImage:
            self.cacheImage = self.buildImages()
        return self.cacheImage

    @abstractmethod
    def buildImages(self):
       return {}

class CharGlyph(Glyph):
    '''A Glyph that represents a character. The images are built by drawing the character on a transparent background. The character is drawn at the center of the canvas. The images are built for each half of the panel (top and bottom) and for the whole panel. The images are built on demand and cached for future use.
    '''

    def __init__(self, character, size, font, fontSize) -> None:
        '''character: the character to display
        size: a tuple (width, height) that defines the size of the glyph. The size of the panel is defined by the size of the glyph and the padding between the glyphs.
        font: the font to use to draw the character
        fontSize: the size of the font to use to draw the character '''
        super().__init__(size)
        self.font = font
        self.fontSize = fontSize
        self.character = character


    def buildImages(self):
        '''Build the images to display for each half of the panel. The images are stored in a dictionary with the keys being the image type (whole, top, bottom) and the values being the images to display for each half of the panel. The whole image is used when the panel is not rotating, the top and bottom images are used when the panel is rotating. The images are built by drawing the character on a transparent background. The character is drawn at the center of the canvas. The images are built on demand and cached for future use.'''

        # retrieve width and height
        size = width, height= self.size

        # Create a new Image object with the desired dimensions
        transparent_color = (150, 150, 150, 45) # (30,30,30,255)  
        font = self.font

        
        image = PIL.Image.new("RGBA", size, transparent_color)

        # Create a drawing object to draw on the image
        draw = PIL.ImageDraw.Draw(image)

        # Draw a character at the center of the canvas
        mask = font.getmask(self.character)
        iWidth, _ = mask.size
        position = (width - iWidth) // 2,  (height - self.fontSize) // 2

        draw.text(position, self.character, font=font)

        # flip image vertically
        image = image.transpose(PIL.Image.FLIP_TOP_BOTTOM) # type: ignore

        height_mid = height //2

        images = { 
            ic.WHOLE:image, 
            ic.TOP:image.crop((0,height_mid,width,height)),
            ic.BOTTOM:image.crop((0,0,width,height_mid)),
            }

        return images

        

class GlyphSet:
    '''A set of glyphs that can be displayed on the panel. The glyphs are stored in a dictionary with the keys being the glyph code and the values being the glyph objects. The glyph code is a string that represents the character to display. The glyph objects are built on demand and cached for future use. The glyphs are built by the buildStandard method that need to be implemented by the subclass. The getGlyph method returns the glyph object for a given glyph code. The findNextGlyphCode method returns the next glyph code in the set for a given glyph code. The next glyph code is determined by the order of the keys in the dictionary.
    '''
    
    def __init__(self, glyphSize) -> None:
        self.glyphs = {}
        self.glyphSize = glyphSize

    def addGlyph(self, code:str, glyph):
        '''Add a glyph to the set. The glyph is stored in a dictionary with the key being the glyph code and the value being the glyph object. The glyph code is a string that represents the character to display. The glyph objects are built on demand and cached for future use. The glyphs are built by the buildStandard method that need to be implemented by the subclass. The getGlyph method returns the glyph object for a given glyph code. The findNextGlyphCode method returns the next glyph code in the set for a given glyph code. The next glyph code is determined by the order of the keys in the dictionary.'''
        #assert (code not in self.glyphs)
        self.glyphs[code] = glyph

    @staticmethod
    def buildStandard(glyphSize, fontSize):
        '''Build a standard set of glyphs that can be displayed on the panel. The glyphs are stored in a dictionary with the keys being the glyph code and the values being the glyph objects. The glyph code is a string that represents the character to display. The glyph objects are built on demand and cached for future use. The glyphs are built by drawing the character on a transparent background. The character is drawn at the center of the canvas. The images are built for each half of the panel (top and bottom) and for the whole panel. The images are built on demand and cached for future use.'''
        font = PIL.ImageFont.truetype(DEFAULT_FONT_FILE_PATH,size=fontSize) 
        # build char glyphs
        glyphSet = GlyphSet(glyphSize=glyphSize)
        for character in ALL_CHARS:
            glyphSet.addGlyph(character, CharGlyph(character=character, size=glyphSize, font=font, fontSize=fontSize))

        return glyphSet 

    def getGlyph(self, glyphCode):
        
        if glyphCode in self.glyphs:
            return self.glyphs[glyphCode]
        else:
            raise Exception (f"Unknown glyphCode '{glyphCode}'")
        
    def findNextGlyphCode(self, glyphCode):
        if glyphCode in self.glyphs:
            lk = list(self.glyphs.keys())
            i = lk.index(glyphCode)
            nextGlyphCode=lk[(i+1)%len(lk)]
            return nextGlyphCode
        else:
            raise Exception (f"Unknown glyphCode '{glyphCode}'")

    def findPreviousGlyphCode(self, glyphCode):
        if glyphCode in self.glyphs:
            lk = list(self.glyphs.keys())
            i = lk.index(glyphCode)
            nextGlyphCode=lk[(i-1)%len(lk)]
            return nextGlyphCode
        else:
            raise Exception (f"Unknown glyphCode '{glyphCode}'")


class GlyphPort:
    '''A symbol object to display'''

    MAX_CLICK = 3

    def __init__(self, glyphPanel, sound=None) -> None:
        self.glyphPanel = glyphPanel
        self.sound = sound if sound else glyphPanel.sound
        self.currentGlyphCode = " " #random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        self.currentGlyphTime = None
        self.targetGlyphCode = ' '
        rotationSpeed = self.glyphPanel.getPortRotationSpeed()
        self.rotationSpeed = rotationSpeed # random alternative =   int(rotationSpeed *random.lognormvariate(1/math.exp(1),.05))
        self.flashFlag = False
        self.wake()

    def sleep(self, milliseconds):
        self.sleepUntil = datetime.datetime.now() + datetime.timedelta(milliseconds=milliseconds)

    def wake(self):
        self.sleep(0)

    def makeRelaySound(self):
        
        def makeSound():
            wavContent = self.glyphPanel.getRelaySound()
            play_obj = wavContent.play()
            play_obj.wait_done()
            GlyphPort.MAX_CLICK += 1
        
        # test if sound is requested on panel
        if self.sound:
            if GlyphPort.MAX_CLICK>0:
                GlyphPort.MAX_CLICK -= 1
                sound_thread = threading.Thread(target=makeSound)
                sound_thread.start()

    def setNewTargetGlyph(self, glyphCode):
        gs = self.glyphPanel.glyphSet
        if glyphCode not in gs.glyphs:
            glyphCode = glyphCode.upper()
        self.targetGlyphCode = glyphCode


    def drawHalf(self, canvas, glyphCode, topOrBottom:ic, fraction):
        '''Draw half of a panel '''

        # retrieve glyph by code
        glyphSet = self.glyphPanel.glyphSet
        glyph = glyphSet.getGlyph(glyphCode)

        # retrieve the image to draw
        images = glyph.getImages()
        image = images[topOrBottom]

        # get the height of the glyph
        _, h = glyph.size
        
        # calculate the height from which to start drawing
        y0Map = {
            ic.TOP: h / 2.0, 
            ic.BOTTOM: h /2.0 * (1.0-fraction),
        }

        y0 = y0Map[topOrBottom]

        canvas.drawImage(image, y0=y0, verStretch=fraction)
       
    def flash(self):
        self.flashFlag=True

    def draw(self, canvas, time):

        rotSpeed = self.rotationSpeed

        # init time for the first time
        if not self.currentGlyphTime:
            self.currentGlyphTime = time

        if time<self.sleepUntil:
            self.currentGlyphTime = time
        else:
            if (self.currentGlyphCode == self.targetGlyphCode) and not self.flashFlag:
                self.currentGlyphTime = time



        dt = time - self.currentGlyphTime
        ms = dt.microseconds / 1000.0 + dt.seconds * 1000.0


        glyphSet = self.glyphPanel.glyphSet
        nextGlyphCode = glyphSet.findNextGlyphCode(self.currentGlyphCode)

        if ms < rotSpeed // 32:
            self.drawHalf(canvas, self.currentGlyphCode, ic.TOP, fraction=1.0)
            self.drawHalf(canvas, self.currentGlyphCode, ic.BOTTOM, fraction=1.0)

        elif ms < rotSpeed // 2:            
            self.drawHalf(canvas, nextGlyphCode, ic.TOP, 1.0)
            self.drawHalf(canvas, self.currentGlyphCode, ic.TOP, fraction= 1.0 - ms / rotSpeed * 2.0 )
            self.drawHalf(canvas, self.currentGlyphCode, ic.BOTTOM, fraction=1.0)

            
        elif ms<rotSpeed:
            self.drawHalf(canvas, nextGlyphCode, ic.TOP, 1.0)
            self.drawHalf(canvas, self.currentGlyphCode, ic.BOTTOM, fraction=1.0)
            self.drawHalf(canvas, nextGlyphCode, ic.BOTTOM, fraction = (ms-rotSpeed/2) *2.0 / rotSpeed)
            

        else:
            self.drawHalf(canvas, nextGlyphCode, ic.TOP, fraction=1.0)
            self.drawHalf(canvas, nextGlyphCode, ic.BOTTOM, fraction=1.0)
            self.currentGlyphCode = nextGlyphCode
            self.currentGlyphTime = time
            self.flashFlag = False
            self.makeRelaySound()

        # Draw midle line
        GLYPH_SIZE = self.glyphPanel.getGlyphSize()
        w, h = GLYPH_SIZE
        p = w / 3
        canvas.drawLine(p,h//2,w-p,h//2, color=Palette.BLACK, width=1.2)


class GlyphRanker:

    def __init__(self, rowLength, rowCount) -> None:

        self.rowLength = rowLength
        self.rowCount = rowCount
        self.cacheFunctionDict = None

    def getRankings(self):
        if not self.cacheFunctionDict:
            funList = (
                        self.default,
                        self.immediate, 
                        self.regular , 
                        self.downByLine,
                        self.rightByColumn,
                        self.topLeft,
                        self.circleOut, 
                        self.circleIn)
            self.cacheFunctionDict = { function.__name__:
                                        self.getIndex(function) for function in funList }
        return self.cacheFunctionDict

    def getIndex(self, function):
        glyph_list = []
        for row in range(self.rowCount): 
            for col in range(self.rowLength):
                glyph_list.append((col, row, *function(col, row)))
        sl = sorted(glyph_list, key=lambda element:element[-1])
        return [element[:-1] for element in sl]

    def default(self, col, row):
        return self.downByLine(col, row)

    def immediate(self, col, row):
        return 0, 1

    def regular(self, col, row):
        return 1, col + (self.rowCount - row -1) * self.rowLength
    
    def downByLine(self, col, row):
        timeSpan = self.rowLength if col==self.rowLength-1 else 0
        v = -row * self.rowLength - col
        return timeSpan, v

    def rightByColumn(self, col, row):
        timeSpan = self.rowCount if row == self.rowCount-1 else 0
        v = col * self.rowCount + row
        return timeSpan, v

    def topLeft(self, col, row):
        v = self.rowCount-row+col
        timeSpan = min(row+col,min(self.rowCount, self.rowLength)) if row ==0 else 0
        return timeSpan, v 

    def circleOut(self, col, row):
        return 1, (col-self.rowLength // 2 ) ** 2 + (row - self.rowCount // 2) ** 2
    
    def circleIn(self, col, row):
        return 1, -self.circleOut(col, row)[1]

class GlyphPanel:

    def __init__(self, glyphSet, glyphSize, glyphPadding, panelDimension, portRotationSpeed, portRefreshLapse, sound) -> None:
        self.glyphSet = glyphSet
        self.glyphSize = glyphSize
        self.glyphPadding = glyphPadding
        self.panelDimension = panelDimension
        self.portRotationSpeed = portRotationSpeed
        self.portRefreshLapse = portRefreshLapse
        self.audioCache = None
        self.getRelaySound()
        self.panelStartTime = datetime.datetime.now()
        self.sound = sound

        # init ports
        self.initGlyphPorts()

        self.rankings = GlyphRanker(*self.panelDimension).getRankings()

    def getGlyphSize(self):
        return self.glyphSize

    def flash(self):
        '''
        force a manual refresh of the panel by advancing one glyph on each port. 
        This is useful to trigger the animation and sound when the text is updated.
        '''
        for glyphPortRow in self.glyphPorts:
            for glyphPort in glyphPortRow:
                glyphPort.flash()


    def getRelaySound(self):

        if not self.audioCache:
            self.audioCache = simpleaudio.WaveObject.from_wave_file(str(RELAY_SOUND_PATH))

        return self.audioCache

    def getPortRotationSpeed(self):
        return self.portRotationSpeed

    def initGlyphPorts(self):

        # retrieve size
        rowLength, rowCount = self.panelDimension

        # populate panel with Glyphs
        glyphPorts = []
        for _ in range(rowCount):
            glyphPortRow = [GlyphPort(self) for _ in range(rowLength)]
            glyphPorts.append(glyphPortRow)

        self.glyphPorts = glyphPorts

    def updateText(self, text:str):
        '''
        Display a text on the panel. The text is a string where each line is separated by a slash. 
        The number of lines is determined by the number of rows in the panel. The number of characters per line is determined by the number of columns in the panel. If the text is too long, 
        it will be truncated. If the text is too short, it will be padded with spaces.
        '''

        self.flash() # trigger animation and sound for the update of the text by advancing one glyph on each port. This is useful to trigger the animation and sound when the text is updated. The text will be updated in the next draw cycle.

        rankings = self.rankings

        ranker = random.choice(list(rankings.values()))

        '''cols, rows = self.panelDimension
        text2 = text.split("<br")
        text2 = "<br>".join([f"{t: >{cols}}" for t in text2])
        text2 = text2.replace(" ","A")'''

        self.updateText_(text, ranker )  # update the text on the panel with the original text after a delay. This is useful to trigger the animation and sound for the update of the text by advancing one glyph on each port. The text will be updated in the next draw cycle.



    def updateText_(self, text:str, ranker=None):
        '''
        Display a text on the panel.

        text: a slash separated string where each segment represent a line 
        '''

        lineSize, rowCount = self.panelDimension

        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

        def g(t,pos=0):
            if pos>=len(t):
                return []
            else:
                a,b,c = t[:pos], t[pos], t[pos+1:]
                b_lower = b.lower()
                b_upper = b.upper()
                t_lower = a+b_lower+c
                t_upper = a+b_upper+c
                
                result = [t_lower,t_upper]
                result.extend(g(t_lower,pos+1))
                result.extend(g(t_upper,pos+1))     
                result = list(set(result))           
                return result
        
        br = "<br>"
        for t in g(br):
            text=text.replace(t,br)

        lines = text.split(br)[:rowCount]

        extraSep = [''] * (rowCount-len(lines))
        lines += extraSep
       
        sleepDelay = 0

        if ranker:
            for col, row, timeSpan in ranker:
                self.glyphPorts[row][col].sleep(sleepDelay)
                sleepDelay += self.portRefreshLapse * timeSpan * random.lognormvariate(1/math.exp(1),.1)

        for row, line in enumerate(lines):
            line = line[:lineSize].ljust(lineSize)
            for col, symbol in enumerate(line):
                # retrieve glyphPort
                glyphPort = self.glyphPorts[rowCount-row-1][col]
                glyphPort.setNewTargetGlyph(symbol)


    def getSize(self):
        '''Get width and heigh of the panel area'''
        rowLength, rowCount = self.panelDimension
        w, h = self.glyphSize
        padding = self.glyphPadding
        panelWidth = (rowLength-1) * (w + padding) + w + DEFAULT_PANEL_PADDING*2
        panelHeight = (rowCount-1) * (h+padding) + h + DEFAULT_PANEL_PADDING*2
        return panelWidth, panelHeight

    def draw(self, canvas, time):
            self.drawPanel(canvas, time)
            self.drawStatus(canvas, time)


    def drawPanel(self, canvas, time):

        (glyphWidth, glyphHeight),padding = self.glyphSize, self.glyphPadding

        x0,y0= DEFAULT_PANEL_PADDING, DEFAULT_PANEL_PADDING

        # draw all glyphs
        for row, rowGlyphPort in enumerate(self.glyphPorts):
            for col, glyphPort in enumerate(rowGlyphPort):
                x1 , y1 = x0+col*(glyphWidth+padding), y0+row*(glyphHeight+padding)
                canvasRelative = CanvasRelative(canvas,x1, y1)
                glyphPort.draw(canvasRelative, time)

    def drawStatus(self, canvas, time):
        '''Draw flashing green disque on the panel'''
        if (time.second) % 2 == 0:
            w,h = self.getSize()
            w-= DEFAULT_PANEL_PADDING * 3 / 4
            h-= DEFAULT_PANEL_PADDING + self.glyphSize[1] // 2
            diam=1.5
            canvas.drawCircle(w, h, diam, color=Palette.GREEN, width=diam)

class SolariApp(GraphicApp):

    def __init__(self, 
                 graphicInterface,
                 feeder:Feeder = Feeder.default(),
                 framePerSecond=DEFAULT_FRAME_PER_SECOND,
                 glyphSize=DEFAULT_GLYPH_SIZE,
                 fontSize = DEFAULT_FONT_SIZE,
                 glyphPadding=GLYPH_PADDING,
                 panelSize= DEFAULT_PANEL_SIZE,
                 panelPadding = DEFAULT_PANEL_PADDING,
                 portRotationSpeed = DEFAULT_ROTATION_SPEED,
                 portRefreshLapse = DEFAULT_PORT_REFRESH_LAPSE,
                 sound = DEFAULT_SOUND,
                 ) -> None:
        
        # call ancestor constructor
        super().__init__(graphicInterface=graphicInterface, framePerSecond=framePerSecond)
        
        # set feeder
        self.feeder = feeder

        # set window title
        self.title = "Solari Board"
        self.graphicInterface.setTitle(self.title)


        # calculate size requirement base on characteristics of the panel
        rowLength, rowCount = panelSize
        w, h = glyphSize
        sizeRequirement = (rowLength-1) * ( w + glyphPadding) + w + panelPadding*2, \
                            (rowCount-1) * (h+glyphPadding) + h + panelPadding*2

        self.setSizeRequirement(sizeRequirement)
        
        # build glyphset
        self.glyphSet = GlyphSet.buildStandard(glyphSize=glyphSize, fontSize=fontSize)

        # build panel
        self.panel = GlyphPanel(
            glyphSet=self.glyphSet,
            glyphSize=glyphSize, 
            glyphPadding=glyphPadding,
            panelDimension=panelSize, 
            portRotationSpeed=portRotationSpeed,
            portRefreshLapse=portRefreshLapse,
            sound=sound)

        self.graphicInterface.onKeyEvent.bind(self._on_keyboard)

        # initialize message0 to an empty message to avoid errors when the user clicks on the panel before the first message is loaded from the feeder
        self.message0 = None

        # wait a bit before starting to display messages to let the user see the panel before it starts refreshing
        time.sleep(3)

        logger.info("Starting SolariApp with feeder: "+str(feeder))

        # initiate cycling messages from feeder
        self._cycle()

    def _on_keyboard(self, key, scancode, codepoint, modifier):
        '''Handle keyboard events. Press 'f' to toggle fullscreen mode.'''
        
        if codepoint == 'f':
            self.graphicInterface.toggleFullScreen()
            return True
        
        elif codepoint == 'l':
            if self.message0 and self.message0.link:
                url = self.message0.link
                logger.info(f"Opening link {url} in browser")
                webbrowser.open(url)
                return True
            else:
                logger.error('No link to open')
                return False
        
        return False

    def _cycle(self):

        # obtain next message from the feeded
        message = self.feeder.next()
        
        # have the method call each other again for the next message to display
        timer = threading.Timer(message.displayTimeInSeconds, self._cycle)
        timer.daemon = True
        timer.start()


    def draw(self, canvas, time):
        
        # get text from feeder
        message = self.feeder.getMessage()

        # update panel if string has changed
        if not self.message0 or message.text != self.message0.text:
            self.panel.updateText(message.text)
            self.message0 = message.copy()

        # draw panel
        self.panel.draw(canvas, time)



   