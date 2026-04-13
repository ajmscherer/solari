
from pathlib import Path
import logging
import re
from datetime import datetime
import pytz
import schedule 
import time
from threading import Thread

BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "resources"
PROMPT_DIR = RESOURCES_DIR / "prompts"
CACHE_DIR = BASE_DIR / "cache"


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)


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
        logging.info(f"Scheduler {self} started")

        self.counter = 0

        def target():
            self.counter +=1
                
            # log update
            linfo = f"Scheduler {self} calls {self.targetFunction} #{self.counter}"
            if self.limit:
                linfo += f" OF {self.limit}"
            logging.info(linfo)

            self.targetFunction()

            if self.limit: 
                if self.counter == self.limit:
                    self.stop()
                    

        # start targetFunction immediately
        target()

        # schedule calls to targetFunction every refresh_cycle
        schedule.every(self.interval).minutes.do(target)
        
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        
        thread = Thread(target=run_scheduler, daemon=True)
        thread.start()
    
    def stop(self):
        self.running = False
        logging.info(f"Scheduler {self} stopped")


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

    def next(self):
        '''Return the next value in the list. The list is obtained by calling the getList function. The index is incremented by 1. If the index is greater than the length of the list, it is reset to 0.'''
        data = self.getList()
        length = len (data)
        if length>0:
            result= data[self.index % length]
        else:
            result = None
        self.index +=1

        return result

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

''' Helper function'''

def convertDate2String(date:datetime):
    return date.isoformat()

def parseGMDDatetime(string, localTimeZone):
    # Step 1: Parse the GMT string into a naive datetime object
    gmt_string = "2026/04/09 23:15:00"
    dt_naive = datetime.strptime(gmt_string, "%Y/%m/%d %H:%M:%S")

    # Step 2: Localize it to UTC (since it's GMT)
    utc = pytz.UTC
    dt_utc = utc.localize(dt_naive)

    # Step 3: Convert to Miami's local time (Eastern Time)
    local = pytz.timezone(localTimeZone)
    dt_local = dt_utc.astimezone(local)

    # Now dt_miami is a timezone-aware datetime object in Miami's local time
    return dt_local

def getPromt(filename:str):
    extension = ".txt"
    if not filename.endswith(extension):
        filename = filename + extension
    return (PROMPT_DIR / filename).read_text()

