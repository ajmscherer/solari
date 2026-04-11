'''
Code that simulates a Split-Flap or Solari board

A Scherer
2024 

'''

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

import simpleaudio
import threading

import random

from grabst import CanvasRelative, GraphicApp, Palette

import datetime
from abc import ABC, abstractmethod
from enum import Enum, auto
import math

import unidecode

from feeder import Feeder

from common import RESOURCES_DIR

# Definition of constants


DEFAULT_SOURCE_TEXT_PATH = RESOURCES_DIR / "poeme.txt"

DEFAULT_ROTATION_SPEED = 125  # time in milliseconds to go from one charactere to the next
DEFAULT_FRAME_PER_SECOND = 24

DEFAULT_GLYPH_SIZE = 30, 60,
GLYPH_PADDING = 6
DEFAULT_FONT_SIZE = 45

#DEFAULT_GLYPH_SIZE = 26,40
#GLYPH_PADDING = 3
#DEFAULT_FONT_SIZE = 32

DEFAULT_PANEL_SIZE = 30 , 7
DEFAULT_PANEL_PADDING = 50
DEFAULT_PORT_REFRESH_LAPSE = 10 # time in milliseconds for the panel to deal with one port to the next when refreshing 
DEFAULT_SOUND = False

#all_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!#$%&*()-=+;:\",<.>/? "
ALPHA_CHAR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALL_CHARS = " 01234567890"+ALPHA_CHAR+"!'\"$%&*-=+:,.?"


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

    def __init__(self, size) -> None:
        super().__init__()
        self.cacheImage = None
        self.size = size

    def getImages(self):
        if not self.cacheImage:
            self.cacheImage = self.buildImages()
        return self.cacheImage

    @abstractmethod
    def buildImages(self):
       return {}

class CharGlyph(Glyph):

    def __init__(self, character, size, font, fontSize) -> None:
        super().__init__(size)
        self.font = font
        self.fontSize = fontSize
        self.character = character


    def buildImages(self):
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

    def __init__(self, glyphSize) -> None:
        self.glyphs = {}
        self.glyphSize = glyphSize

    def addGlyph(self, code:str, glyph):
        #assert (code not in self.glyphs)
        self.glyphs[code] = glyph

    @staticmethod
    def buildStandard(glyphSize, fontSize):
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

        
    def draw(self, canvas, time):

        rotSpeed = self.rotationSpeed

        # init time for the first time
        if not self.currentGlyphTime:
            self.currentGlyphTime = time

 
        if (self.currentGlyphCode == self.targetGlyphCode) or (self.sleepUntil > time):
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
        Display a text on the panel.

        text: a slash separated string where each segment represent a line 
        '''

        lineSize, rowCount = self.panelDimension

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


        rankerName = random.choice(list(self.rankings.keys()))
        #rankerName = 'downByLine'
        ranker = self.rankings[rankerName]
        print(rankerName)
        
        sleepDelay = 0

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

        panelWidth, panelHeight = self.getSize()

        canvasWidth, canvasHeight = canvas.getSize()

        (glyphWidth, glyphHeight),padding = self.glyphSize, self.glyphPadding

        #x0 , y0 = (canvasWidth-panelWidth) // 2 , (canvasHeight-panelHeight) // 2
        x0,y0= DEFAULT_PANEL_PADDING, DEFAULT_PANEL_PADDING

        # draw all glyphs
        for row, rowGlyphPort in enumerate(self.glyphPorts):
            for col, glyphPort in enumerate(rowGlyphPort):
                x1 , y1 = x0+col*(glyphWidth+padding), y0+row*(glyphHeight+padding)
                canvasRelative = CanvasRelative(canvas,x1, y1)
                glyphPort.draw(canvasRelative, time)

    def drawStatus(self, canvas, time):
        '''Draw status information on the panel'''
        if (time.second // 2) % 2 == 0:
            w,h = self.getSize()
            w-= DEFAULT_PANEL_PADDING * 3 / 4
            h-= DEFAULT_PANEL_PADDING + self.glyphSize[1] // 2
            diam=1.5
            canvas.drawCircle(w, h, diam, color=Palette.GREEN, width=diam)

class TextParser:

    def __init__(self, lines, glyphPanel, rankerName) -> None:
        self.lines = lines
        self.glyphPanel = glyphPanel
        self.rankerName = rankerName
        self.pos = 0


    @staticmethod 
    def loadFromFile(path, glyphPanel, rankerName = "default"):
        lines = []
        with open(path, "r") as file:
            for line in file:
                lines.append(line.strip('\n'))
                lines.append('')
        return TextParser(lines=lines, glyphPanel=glyphPanel, rankerName=rankerName)
            


    def formatLines(self, line):

        rowLength, _ = self.glyphPanel.panelSize

        cm = min(rowLength, len(line))

        def formatLinesWithoutToken(line):
            # retrieve panel size
            rowLength, rowCount = self.glyphPanel.panelSize
            
            lines = []

            def eatWord(cursor0):
                cursor1 = cursor0
                while cursor1<cm and line[cursor1] in ALPHA_CHAR:
                    cursor1 +=1
                result = line[cursor0:cursor1]
                cursor0 = cursor1
                return cursor0, result

            def eatSep(cursor0):
                if cursor0 <cm and line[cursor0] not in ALPHA_CHAR:
                    return cursor0+1, line[cursor0]
                else:
                    return cursor0, ""

            # remove accents
            lineUnidecoded = unidecode.unidecode(line)

            lines.append(lineUnidecoded)
            
            return lines

        return formatLinesWithoutToken(line)

    def readNextBlock(self):
        block=[]

        # retrieve panel size
        _, rowCount = self.glyphPanel.panelSize

        while len(block)<rowCount:
            line = self.lines[self.pos]
            formatedLines = self.formatLines(line)
            block.extend(formatedLines)
            self.pos = (self.pos + 1) % len(self.lines)
            if self.pos == 0:
                break
        return block


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
        self.title = "Solari Board Simulator"
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

        # init lifeflag
        self.lifeFlag = None

        self.string_current = ""

    def draw(self, canvas, time):
        
        # get text from feeder
        string = self.feeder.getString(time)

        # update panel if string has changed
        if string != self.string_current:
            self.panel.updateText(string)
            self.string_current = string

        # draw panel
        self.panel.draw(canvas, time)



    def draw_old(self, canvas, time):

        now = datetime.datetime.now()

        rowLength, rowCount = self.panel.panelDimension

        def fmtTime(dt):
            return f"{dt.hour:0>2}h{dt.minute:0>2}".rjust(rowLength)

        messages = [
                    f'{"Miami".rjust(rowLength)}<br><br>{now.strftime("%a %b %d %Y")}<br><br>{fmtTime(now)}<br>HAVE A GOOD DAY!',
                    'AF007 PARIS       16h30 GATE 23<br>'+\
                    'LU032 MUNICH      19h15 GATE 14<br>'+\
                    'AA588 ZURICH      21h12 GATE 42<br>'+\
                    'IB912 MADRID      22h54 GATE 04<br>'+\
                    'RA912 BUCHAREST   22h58 GATE 11<br>'+\
                    'TP126 LISBON      22h58 GATE 11<br>'+\
                    'LU321 ROTTERDAM   23h14 GATE 31<br>',
                    f'{"Welcome".rjust(rowLength)}<br><br>{fmtTime(now)}<br><br>TO THE SOLARI BOARD SIMULATOR',
                           ]

        life = ( time - self.panel.panelStartTime).seconds

        cycleLength = 15

        if  life % cycleLength == 0 and self.lifeFlag!=life:
            self.lifeFlag = life
            cycle = (life // cycleLength) % len(messages)
            message = messages[cycle]
            '''
            message = "/".join(self.textParser.readNextBlock())
            '''    
            self.panel.updateText(message)
            

        self.panel.draw(canvas, time)
