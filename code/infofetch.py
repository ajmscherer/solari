from pathlib import Path
import schedule
from threading import Thread
import os
import feedparser
import time
import textwrap
import hashlib
import pytz
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from common import CACHE_DIR, PROMPT_DIR
import json

import logging


import xai_sdk as xai
import xai_sdk.chat as xai_chat
import xai_sdk.tools as xai_tools

from dotenv import load_dotenv
load_dotenv()

# TASS RSS feed URL 
TASS_RSS_URL = "https://tass.com/rss/v2.xml"
AP_NEWS_URL = "https://apnews.com/index.rss"
MOSCOW_TIME_RSS_URL = "https://www.themoscowtimes.com/rss/news"
XAI_NEWS_RSS_URL = "https://api.x.ai/v1"  # Placeholder URL for XAI news feed


NEWS_GATHERING_PROMPT = "news_gathering.txt"

NEWS_CACHE_FILE_NAME_PREFIX = "cache_info"
INFO_CACHE_FILE_NAME = NEWS_CACHE_FILE_NAME_PREFIX + "_{}_{}.txt"

REFRESH_CYCLE = 30 # in minutes

LOCAL_TIME_ZONE = "US/Eastern"

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

    def __init__(self, source) -> None:
        ''' source : list of object '''
        self.source = source
        self.index = 0

    def next(self):
        data = self.source.as_list()
        length = len (data)
        if length>0:
            result= data[self.index % length]
        else:
            result = None
        self.index +=1

        return result
    
class InfoFetcher(ABC):

    def __init__(self) -> None:
        super().__init__()
        self.setCacheUsageFlag(False)
        self._started = False
        self._scheduler = None
        self.info =[]
        self._vrotation = ValueRotation(self)

    def as_list(self):
        return self.info
    
    def next(self):
        return self._vrotation.next()

    def toSolari(self, record:dict, colWidth:int) -> str:
        return "need override"

    def setCacheUsageFlag(self, flag):
        self._useCache = flag in [True,'on', 'ON']

    def _getClassName(self):
        return self.__class__.__name__

    def start(self, interval=10, limit = None):
        '''schedule regular info fetching'''
        self._scheduler = Scheduler(self.fetch , interval=interval, limit=limit)
        self._scheduler.start()

    def stop(self):
        if self._scheduler:
            self._scheduler.stop()

    def isrunning(self):
        if self._scheduler:
            return self._scheduler.running
        else:
            return False



    def fetch(self):

        if not self._started:
            self._prepare()
            self._started = True
        
        # fetch info
        if self._useCache:
            info = self._fetchFromCache()
        else:
            info = self._fetch()

        # save to cache
        self._saveToCache(info)

        self.info = info

        # return
        return info


    def _fetchFromCache(self):
        className = self._getClassName()
        root = CACHE_DIR
        pattern = INFO_CACHE_FILE_NAME.format(className, "2026*")
        paths = list(root.rglob(pattern))
        info =[]
        for path in paths:
            info.extend( json.load(open(path)))
        return info


    def _saveToCache(self, info):
        '''Save info to cache '''



        # get timestamp
        now = datetime.now().strftime( "%Y.%m.%d %H:%M:%S")
        
        # get class name
        className = self._getClassName()

        # save two files: with with name showing timestamp and one with name showing current
        for param in [now, 'current']:
            file_name = INFO_CACHE_FILE_NAME.format(className, param)
            path = Path(CACHE_DIR / file_name)
            path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    @abstractmethod
    def _getRecordDate(self, record):
        pass

    @abstractmethod
    def _prepare(self):
        '''Do initial prepration work, like openign communication with source and initiating chat'''
        pass

    @abstractmethod
    def _fetch(self)->list:
        '''fetch a batch of fresh info'''

class InfoFetcher_xAI(InfoFetcher):

    def __init__(self, API_key, model, promptInitial, PromptRefresh="Refresh please") -> None:
        super().__init__()
        self.API_key = API_key
        self.model = model
        self.promptInitial = promptInitial
        self.promptRefresh = PromptRefresh


    def _prepare(self):
        os.environ["XAI_API_KEY"] = self.API_key  # Ensure the API key is set in environment variables

        # instantiate XAI Client
        client = xai.Client()

        # create XAI chat with web search and X search capabilities
        tools=[xai_tools.web_search(), xai_tools.x_search()]
        self.chat = client.chat.create(model=self.model, store_messages=True, tools=tools )

        # get initial prompt to prepare the news feed
        response = self.processPrompt(self.promptInitial)

        assert(response=="OK")
        

    def _fetch(self) -> list:
        
        # obtain from XAI a new batch of news
        response = self.processPrompt(self.promptRefresh)
        
        info =[]
        now = datetime.now().strftime( "%Y.%m.%d %H:%M:%S")

        if response:
            news_recs = json.loads(response)
            for news_rec in news_recs:
                title, summary, source, published_GMT, link, id=[news_rec[field] for field in  ( "title", "summary","source","published","link","id")]

                item = {
                        'title': title,
                        'summary': summary,
                        'link': link,
                        'published': published_GMT,
                        'source': source,
                        'fetcher': self._getClassName(),
                        'fetch_timestamp': now,
                        'id': f"XAI-{now}{id}",
                            }
                info.append(item)

        return info
    
    def _getRecordDate(self, record):
        return record['published']

    def processPrompt(self, prompt)->str:
        '''Send a prompt to XAI API and return the response'''
        
        self.chat.append(xai_chat.user(prompt))
        response = self.chat.sample()
        self.chat.append(response)    

        return response.content

class NewsFetcher_TASS(InfoFetcher):

    def _prepare(self):
        pass

    def _fetch(self) -> list:

        def get_item_id(entry):
            """Create a unique ID for each news item"""
            return entry.get('link') or entry.get('id') or hashlib.md5(entry.title.encode()).hexdigest()
        
        # fetch request timestamp
        frt = datetime.now(timezone.utc)
        moscow_tz = pytz.timezone("Europe/Moscow")

        news = []

        try:
            feed = feedparser.parse(TASS_RSS_URL)
            
            if feed.bozo:  # Feed has parsing issues
                logging.warning("Feed parsing issues detected.")
            

            for news_entry in feed.entries:

                item_id = get_item_id(news_entry)
                

                # evaluate published date
                published0 = news_entry.get('published_parsed', news_entry.get('updated_parsed', None))

                if published0:
                    year, month, day, hour, minute, second = [ published0.__getattribute__(field) for field in ['tm_year', 'tm_mon', 'tm_mday', 'tm_hour', 'tm_min', 'tm_sec'] ]
                    published0 = datetime(year=year, month=month, day=day,
                                            hour=hour, minute=minute, second=second)
                    published_moscow = moscow_tz.localize(published0)
                    published = published_moscow.astimezone(timezone.utc)


                else:
                    published = frt  # fallback to fetch request time if no date is available

                # evaluate summary
                if hasattr(news_entry, 'summary'):
                    summary = f"{news_entry.summary[:300]}..." if len(news_entry.summary) > 300 else news_entry.summary
                else:
                    summary = "No summary available."

                # create a record for the news item
                record = {
                    'title': news_entry.title,
                    'summary': summary,
                    'link': news_entry.link,
                    'published': convertDate(published),
                    'source': 'TASS',
                    'fetcher': self._getClassName(),
                    'fetched_timestamp': convertDate(frt),
                    'id': item_id
                }
                news.append (record)
            
                
        except Exception as e:
            logging.error(f"Error fetching feed: {e}")
        
        return news

    def _getRecordDate(self, record):
        return record['published']

    def toSolari(self, record, colWidth=40):
        source, title, summary, published = [record[field] for field in ('source', 'title', 'summary', 'published')]
        tstamp = published[:-3]
        FirstLine = f"{tstamp}{source: >{colWidth-len(tstamp)}}"
        TitleLine = "<br>".join(textwrap.wrap(title, width=colWidth))

        solari= f"{FirstLine}<br><br>{TitleLine}"
        solari = solari.replace("—", "-")
        solari = solari.replace("’", "'")


        return solari
    
''' Helper function'''

def convertDate(date:datetime):
    return date.strftime("%Y.%m.%d %H:%M:%S")

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

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)


''' tests '''

def testFetcher():
    pr0 = PROMPT_DIR / "news_gathering.txt"
    fetcher1 = InfoFetcher_xAI( os.getenv("XAI_API_KEY"), 
                                model="grok-4-1-fast-reasoning", 
                                promptInitial=pr0)
    fetcher1.setCacheUsageFlag(True)

    fetcher2 = NewsFetcher_TASS()
    
    fetcher2.start(interval=1, limit=2)

    while fetcher2.isrunning():
        record = fetcher2.next()
        if record:
            solariText = fetcher2.toSolari(record)
            logging.info(f'SOLARI : {solariText} ')
        time.sleep(5)

    

    

if __name__ == "__main__":
    # test_TASSNewsFeed()
    # test_XAI_NewsFeed()
    testFetcher()