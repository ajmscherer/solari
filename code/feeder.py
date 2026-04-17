from abc import  abstractmethod
from common import Message, Helper
from infofetch import InfoFetcher, NewsFetcher

logger = Helper.supplyLogger()


class Feeder:

    def __init__(self) -> None:
        self._message = Message("Welcome to Solari Panel")

    def getMessage(self):
        return self._message

    def next(self):
        self._message = self._getNextMessage()
        return self._message
    
    @abstractmethod
    def _getNextMessage(self)->Message:
        '''to be ovridden. form next message'''

    @staticmethod
    def default():
        '''Return a default feeder that returns a static string.'''

        return FeederStatic(['Hello World!', '<br>Welcome to<br>  the Solari Board Simulator', '<br><br>Have a nice day!'], 
                            rotationTime='15 seconds')

    @staticmethod
    def charmap(panelSize, startchar=32, lastchar=126):
        '''Return a feeder that returns a character map. The character map is a string that contains the characters from startchar to lastchar, arranged in a grid of columns and rows. The character map is rotated every rotationTime seconds. The default rotation time is 40 seconds.'''

        return FeederStatic(buildCharMap(panelSize=panelSize, startchar=startchar, lastchar=lastchar), rotationTime='40 seconds')

class FeederStatic(Feeder):

    def __init__(self, contents, rotationTime='40 seconds'):
        '''A feeder that returns a static string. The string can be rotated every rotationTime seconds.
         - contents: a list of strings to rotate through. If the list is empty, the feeder will return an empty string. If the list has one element, the feeder will return that element. If the list has more than one element, the feeder will rotate through the elements every rotationTime seconds.
         - rotationTime: the time in seconds to rotate through the strings.
        '''
        super().__init__()
        self.rotationTime = rotationTime
        self.contents = contents
        self.pos = 0
        if len(contents)<1:
            logger.error('contents is a list that must contain at least one string')
            self.contents = ['no list provided for FeederStatic']
        



    def _getNextMessage(self) -> Message:

        strings = self.contents
        text = strings[self.pos % len(strings)]
        self.pos += 1

        return Message(text, self.rotationTime)

class FeederInfo(Feeder):

    @staticmethod
    def buildFromInfoSource(news_source, panelSize:tuple[int,int], **kwargs):
        '''
        Return a feeder that fetches information from the given news source. 
        If the news source is not found in the InfoSource enum, an exception is raised.
        '''
        try:
            newsFetcher = NewsFetcher.find(news_source)
            try:
                newsFetcher.start()
                return FeederInfo(fetcher=newsFetcher, panelSize=panelSize, **kwargs)
            
            except Exception as e:
                logger.error(f"Error starting feeder for source {news_source}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error building feeder for source {news_source}: {e}")
            raise

    def __init__(self, fetcher: InfoFetcher, panelSize:tuple[int,int], **kwargs) -> None:
        super().__init__(**kwargs)
        self.fetcher = fetcher
        self.panelSize = panelSize
        self.pos = 0

    def _getNextMessage(self) -> Message:

        record = self.fetcher.next()

        message = self.fetcher.recordAsSolariMessage(record, self.panelSize)

        self.pos += 1

        return message

class FeederMix(Feeder):
    
    @staticmethod
    def buildFromInfoSource(info_sources, panelSize:tuple[int,int], **kwargs):
        if isinstance(info_sources, str):
            info_sources = info_sources.split(",")
        elif not isinstance(info_sources, list):
            info_sources = [info_sources]
        feeders = []
        for info_source in info_sources:
            try:                
                feeder = FeederInfo.buildFromInfoSource(news_source= info_source, panelSize=panelSize, **kwargs)
                feeders.append(feeder)
            except Exception as e:
                logger.error(f"Error building feeder for source {info_source}: {e}")

        if len(feeders)<1:
            logger.error("No feeders could be built from the provided info sources. Returning a default feeder.")
            return Feeder.default()
        return FeederMix(feeders=feeders)

    def __init__(self, feeders) -> None:
        super().__init__()
        self.feeders = feeders
        self.pos = 0
    
    def _getNextMessage(self) -> Message:
        feeders = self.feeders
        feederCount = len(feeders)
        selectedFeeder = feeders[self.pos % feederCount]
        self.pos +=1
        return selectedFeeder.next()

def buildCharMap(panelSize, startchar=32, lastchar=126):
    '''Build a character map for the Solari board. The character map is a dictionary that maps characters to their corresponding bitmaps. The bitmaps are represented as lists of integers, where each integer represents a line of the bitmap. The lineSize parameter is the number of characters per line in the bitmap. The startchar and lastchar parameters define the range of characters to include in the character map.
        -lineSize: the number of characters per line in the bitmap. The default is 40, which means that the bitmap will have 40 characters per line.
        -startchar: the ASCII code of the first character to include in the character map. The default is 32, which is the space character.
        -lastchar: the ASCII code of the last character to include in the character map. The default is 126, which is the tilde character.
    ''' 

    def display(c):
        return "{:0>3}:{} ".format(c,chr(c))

    columns, rows = panelSize
    colCapacity = columns // len(display(startchar))
    pageCapacity = colCapacity * rows

    charRange = range(startchar, lastchar+1)

    nbPages = len(charRange) // pageCapacity + 1

    strings =[['' for r in range(rows)] for p in range(nbPages)]

    for k, char in enumerate(charRange):
        page = k // pageCapacity
        row = (k % pageCapacity) % rows
        strings[page][row]+=display(char)

    strings = ['<br>'.join(strings[page]) for page in range(nbPages)]

    return strings


if __name__ == '__main__':
    s=buildCharMap(panelSize=(30,5))
    print(s)