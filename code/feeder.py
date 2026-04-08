from abc import  abstractmethod

class Feeder:

    @abstractmethod
    def getString(self, time):
        '''Get a string to display on the main window. This method is called by the graphic app. The time parameter is a datetime object that represents the current time.'''
        
    @staticmethod
    def default():
        '''Return a default feeder that returns a static string.'''

        return FeederStatic(['Hello World!', '<br>Welcome to<br>  the Solari Board Simulator', '<br><br>Have a nice day!'], 
                            rotationTime=15)

    @staticmethod
    def charmap(panelSize, startchar=32, lastchar=126):
        '''Return a feeder that returns a character map. The character map is a string that contains the characters from startchar to lastchar, arranged in a grid of columns and rows. The character map is rotated every rotationTime seconds. The default rotation time is 40 seconds.'''

        return FeederStatic(buildCharMap(panelSize=panelSize, startchar=startchar, lastchar=lastchar), rotationTime=40)

class FeederStatic(Feeder):

    def __init__(self, strings, rotationTime=40):
        '''A feeder that returns a static string. The string can be rotated every rotationTime seconds.
         - strings: a list of strings to rotate through. If the list is empty, the feeder will return an empty string. If the list has one element, the feeder will return that element. If the list has more than one element, the feeder will rotate through the elements every rotationTime seconds.
         - rotationTime: the time in seconds to rotate through the strings.
        '''
        self.rotationTime = rotationTime
        self.strings = strings
        self.time0 = None


    def getString(self, time):

        if self.time0 is None:
            self.time0 = time
        
        strings = self.strings
        sec = (time-self.time0).seconds
        pos = sec // self.rotationTime
        string = strings[pos % len(strings)]

        return string
    
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