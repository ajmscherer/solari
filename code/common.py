import requests
from pathlib import Path
import logging
import re
from datetime import datetime
import textwrap
import schedule 
import time
from threading import Thread

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"
PROMPT_DIR = RESOURCES_DIR / "prompts"
CACHE_DIR = BASE_DIR / "cache"


LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOG_DIR / "solari.log"


class Helper:

    _logger = None
    _name = __name__
    _level = logging.DEBUG
    _logpath = LOG_PATH

    @staticmethod
    def supplyLogger() -> logging.Logger:
        if not Helper._logger:            
            logger =  logging.getLogger(Helper._name)
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

            handler = logging.FileHandler(
                filename=Helper._logpath,      # main log file
                mode='w',                 # write mode
                encoding='utf-8',

                    )
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)-8s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(Helper._level)
            Helper._logger = logger

        return Helper._logger

logger = Helper.supplyLogger()


''' HELPER CLASS '''
class Scheduler:

    def __init__(self, targetFunction,  interval, limit = None) -> None:
        '''
        - targetFunction : function or method to be called
        - interval : number of minutes between two calls of targetFunction
        - limit: number of calls to target method (None = infinite number of calls)
        '''

        assert(limit is None or limit > 0)
        self.targetFunction = targetFunction
        self.interval = interval
        self.limit = limit
        self.running = False

    def start(self):
        self.running = True
        logger.info(f"Scheduler {self} started")

        self.counter = 0

        def target():
            self.counter +=1
                
            # log update
            linfo = f"Scheduler {self} calls {self.targetFunction} #{self.counter}"
            if self.limit:
                linfo += f" OF {self.limit}"
            logger.debug(linfo)

            self.targetFunction()

            if self.limit: 
                if self.counter == self.limit:
                    self.stop()

        target()                    
        
        sc = schedule.Scheduler()
        sc.every(self.interval).minutes.do(target)
      
        def run_scheduler():

            while self.running:
                sc.run_pending()
                time.sleep(1)
        
        thread = Thread(target=run_scheduler, daemon=True)
        thread.start()
   
    def stop(self):
        self.running = False
        logger.info(f"Scheduler {self} stopped")


class ValueRotation:
    '''
    Helper class to rotate through a list of values. The list can change over time, the ValueRotation will always use the latest list of values.
    '''

    def __init__(self, getList) -> None:
        '''
        getList: a function that returns a list of values to rotate through. The list can change over time, the ValueRotation will always use the latest list of values.
        '''
        self.getList = getList
        self.index = 0

    def next(self)->dict:
        '''Return the next value in the list. The list is obtained by calling the getList function. The index is incremented by 1. If the index is greater than the length of the list, it is reset to 0.'''
        data = self.getList()
        length = len (data)
        if length>0:
            result= data[self.index % length]
        else:
            result = {}
        self.index +=1

        return result


class Event:
    
    def __init__(self) -> None:
        self.handlers = []

    def bind(self, handler):
        self.handlers.append(handler)

    def unbind(self, handler):
        self.handlers.remove(handler)

    def call(self, *args, **kwargs):
        for handler in self.handlers:
            handler(*args, **kwargs)

class Message:
    '''
    A message to be displayed on a Solari panel. It is defined by its text, the time it should be displayed and an optional link. 
    '''

    def __init__(self, text, displayTime:str|int = '30 seconds', link:str|None=None ) -> None:
        '''text: the text to be displayed on the Solari panel. It can contain HTML tags for formatting.
        displayTime: the time to display the message on the Solari panel. It can be defined in seconds (e.g. 30) or in a string format (e.g. "30 seconds", "1 minute", "2 hours"). The time_to_seconds function is used to convert the string format to seconds.
        link: an optional link to provide more information about the message. It can be used to redirect the user to a website or to provide more context about the message. It is not displayed on the Solari panel, but it can be used by the application to provide more information about the message when the user interacts with it (e.g. by clicking on it).'''
        
        # The text is expected to be pre-formatted with HTML tags for line breaks and styling, as needed for the Solari panel display.
        self.text = text

        # The display time can be provided as a string (e.g., "30 seconds", "1 minute") or directly as an integer representing seconds. The time_to_seconds function is used to convert the string format to seconds if necessary.
        if isinstance(displayTime, str):
            self.displayTimeInSeconds = time_to_seconds(displayTime) # convert string to seconds
        else:
            self.displayTimeInSeconds = displayTime

        # The link is an optional string that can be used to provide additional information about the message. It is not displayed on the Solari panel, but it can be used by the application to provide more context about the message when the user interacts with it (e.g., by clicking on it).
        self.link = link

    def copy(self):
        displayTime = f"{self.displayTimeInSeconds} seconds"
        return Message(self.text, displayTime, self.link)

    @staticmethod
    def create(dt_utc:datetime, content:str, bottomLine:str, displayTime:str|int, link:str|None, panelSize: tuple[int, int]):
        '''Format a message for display on a Solari panel. The message is formatted to fit the panel size, with the date and time at the top, the content in the middle, and a bottom line at the bottom. The content is wrapped to fit the column width of the panel. The bottom line is truncated if it exceeds the column width. The message is returned as a Message object, which contains the formatted text, the display time, and an optional link.'''    
        
        colWidth, rowCount = panelSize
        bottomLine = " " + bottomLine.replace("_", " ")

        dt_local = dt_utc.astimezone()

        tstamp = f"{dt_local.strftime('%a %b').upper()} {dt_local.day} {dt_local.strftime('%H')}H{dt_local.strftime('%M')}"

        lines = ['' for _ in range(rowCount)]

        lines[0] = tstamp

        wrappedContent=textwrap.wrap(content, width=colWidth)

        for i in range(len(wrappedContent)):
            if i+2<rowCount:
                lines[i+2] = wrappedContent[i]
        BottomLine = lines[-1][:colWidth-len(bottomLine)]
        m = colWidth-len(BottomLine)-len(bottomLine)
        lines[-1] = BottomLine+ " "*m + bottomLine

        # Join the lines with HTML line breaks for the Solari panel display
        solariContent= '<br>'.join(lines)

        message = Message(text=solariContent, displayTime=displayTime, link=link)

        return message


''' HELPER FUNCTIONS '''

def time_to_seconds(time_str: str) -> int:
    """
    Convert a human-readable time string (e.g. "12 minutes", "2 hours 4 minutes 3 secondes")
    into the total number of seconds.
    
    Handles:
    - English units (hours, minutes, seconds) with plurals and common abbreviations
    - French "secondes" / "seconde"
    - Formats with or without spaces (e.g. "1h30m", "2 hours 4 minutes")
    - Extra units like days/weeks for completeness
    
    Returns 0 for empty/invalid input. Ignores unknown units.
    """
    if not time_str or not isinstance(time_str, str):
        return 0
    
    # Unit to seconds mapping (both singular/plural forms included for speed + clarity)
    unit_to_sec = {
        # seconds
        's': 1, 'sec': 1, 'second': 1, 'seconds': 1,
        'seconde': 1, 'secondes': 1,   # French variant from your example
        # minutes
        'm': 60, 'min': 60, 'minute': 60, 'minutes': 60,
        # hours
        'h': 3600, 'hr': 3600, 'hour': 3600, 'hours': 3600,
        # days (bonus for "etc...")
        'd': 86400, 'day': 86400, 'days': 86400,
        # weeks (bonus)
        'w': 604800, 'week': 604800, 'weeks': 604800,
    }
    
    time_str = time_str.lower().strip()
    total_seconds = 0
    
    # Regex finds all "number + unit" pairs (handles "2hours", "30 min", "1h 30m", etc.)
    matches = re.finditer(r'(\d+)\s*([a-z]+)', time_str)
    
    for match in matches:
        value = int(match.group(1))
        unit = match.group(2)
        
        # Direct lookup (most cases)
        multiplier = unit_to_sec.get(unit)
        if multiplier is None:
            # Fallback: strip trailing 's' for any missed plurals
            singular = unit.rstrip('s')
            multiplier = unit_to_sec.get(singular)
        
        if multiplier:
            total_seconds += value * multiplier
    
    return total_seconds


def convertDate2String(date:datetime):
    return date.isoformat()

def getPrompt(filename:str):
    extension = ".txt"
    if not filename.endswith(extension):
        filename = filename + extension
    return (PROMPT_DIR / filename).read_text()


def get_city_from_ip():
    
    '''Fetch the user's city and location information based on their IP address using the ipinfo.io API. If the API call fails, return a default location (Miami, Florida, US) with placeholder coordinates and IP.
    '''
    
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5)
        response.raise_for_status()
        data = response.json()
        result= {
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "loc": data.get("loc"),  # "lat,lon"
            "ip": data.get("ip"),
        }
        
    except requests.RequestException as e:
        logger.warning(f"Unable to fetch location from IP: {e}. Using default location.")

        result = {
            "city": "Miami",
            "region": "Florida",
            "country": "US",
            "loc": "25.7617,-80.1918",  # Miami coordinates
            "ip": "127.0.0.1",  # Placeholder IP
        }
    return result

