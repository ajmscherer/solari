from enum import Enum
from pathlib import Path
import os
import feedparser
import time
import textwrap
import hashlib
import pytz
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from abc import ABC, abstractmethod
from common import CACHE_DIR, PROMPT_DIR, convertDate2String, ValueRotation, Scheduler
import json
import logging

import xai_sdk as xai
import xai_sdk.chat as xai_chat
import xai_sdk.tools as xai_tools

from common import time_to_seconds

from dotenv import load_dotenv
load_dotenv()

class NewsSource(Enum):
    NY_TIMES= ("https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "US/Eastern")
    CGTN= ("https://www.cgtn.com/subscribe/rss/section/world.xml", "Asia/Shanghai")
    FRANCE_24= ("https://www.france24.com/en/rss", "Europe/Paris")
    TIME_OF_INDIA= ("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "Asia/Kolkata")
    BBC= ("http://feeds.bbci.co.uk/news/rss.xml","Europe/London")
    AL_JAZEERA= ("https://www.aljazeera.com/xml/rss/all.xml", "Asia/Qatar")
    TASS= ("https://tass.com/rss/v2.xml", "Europe/Moscow")
    # INTERFAX= ("https://www.interfax.ru/rss.asp", "Europe/Moscow")
    THE_GUARDIAN= ("https://www.theguardian.com/world/rss", "Europe/London")
    # PR_NEWSWIRE= ("https://www.prnewswire.com/rss/news-releases-list.rss", "US/Eastern")

# TASS RSS feed URL 
AP_NEWS_URL = "https://apnews.com/index.rss"
MOSCOW_TIME_RSS_URL = "https://www.themoscowtimes.com/rss/news"
XAI_NEWS_RSS_URL = "https://api.x.ai/v1"  # Placeholder URL for XAI news feed


NEWS_GATHERING_PROMPT = "news_gathering.txt"

NEWS_CACHE_FILE_NAME_PREFIX = "cache_info"
AGGREGATE_CACHE_FILE_NAME = NEWS_CACHE_FILE_NAME_PREFIX + "_{}_aggregate.txt"

REFRESH_CYCLE = 30 # in minutes

LOCAL_TIME_ZONE = "US/Eastern"



class Message:
    '''
    A message to be displayed on the panel. It is defined by its text, the time it should be displayed and an optional link. The time to display is defined in seconds and can be converted from a string format (e.g. "30 seconds", "1 minute", "2 hours") using the time_to_seconds function. The link is optional and can be used to provide more information about the message. The message can be copied using the copy method, which creates a new message with the same text, display time and link.
    '''

    def __init__(self, text, displayTime:str = '30 seconds', link:str="", fetcher=None ) -> None:
        '''text: the text to display on the panel
        displayTime: the time to display the message on the panel, defined in seconds or in a string format (e.g. "30 seconds", "1 minute", "2 hours") that can be converted to seconds using the time_to_seconds function'''
        self.text = text
        self.displayTimeInSeconds = time_to_seconds(displayTime) # convert string to seconds
        self.link = link

    def copy(self):
        displayTime = f"{self.displayTimeInSeconds} seconds"
        return Message(self.text, displayTime, self.link)

class InfoFetcher(ABC):
    '''An InfoFetcher is a class that fetches information from a source and provides it in a format that can be displayed on the panel. The information is defined as a list of records, where each record is a dictionary that contains the information to display. The InfoFetcher class provides methods to fetch the information, to get the most recent information, to convert a record to a message that can be displayed on the panel, and to manage the cache of the fetched information. The InfoFetcher class is an abstract class that needs to be subclassed to implement the specific fetching logic for each source of information. The subclass needs to implement the _fetch method that fetches the information from the source and returns it as a list of records, and the _getRecordDate method that returns the date of a record as a datetime object. The InfoFetcher class also provides a start method that schedules regular fetching of the information at a specified interval, and a stop method that stops the scheduled fetching.'''

    def __init__(self, sourceName, timeWindow= '24 hours') -> None:
        '''sourceName: the name of the source of information, used for caching and logging purposes
        timeWindow: the time window for which to display information, defined in seconds or in a string format (e.g. "24 hours", "1 day") that can be converted to seconds using the time_to_seconds function. Only the information that is published within the time window will be displayed on the panel. The time window is used to filter the fetched information and to determine which information is considered recent and should be displayed on the panel.'''

        super().__init__()
        self.setCacheUsageFlag(False)
        self.sourceName = sourceName
        self._started = False
        self._scheduler = None
        self.info =[]
        self.timeWindowSeconds = time_to_seconds(timeWindow)
        self._vrotation = ValueRotation(self.mostRecentInfo)

    def getInfo(self):
        return self.info
    
    def mostRecentInfo(self):
        '''Return the most recent information that is published within the time window. The time window is defined by the timeWindowSeconds attribute and is used to filter the fetched information and to determine which information is considered recent and should be displayed on the panel. The method returns a list of records that are published within the time window. If no information is published within the time window, a default record is returned that indicates that no recent news is available.'''
        info = self.getInfo()
        windowStartTime = datetime.now(timezone.utc)- timedelta(seconds=self.timeWindowSeconds)
        recentInfo = [record for record in info if self._getRecordDate(record) >= windowStartTime]
        if len(recentInfo)==0:
            logging.warning(f"No recent info found for {self.sourceName} in the last {self.timeWindowSeconds} seconds.")
            recentInfo = [{'published': datetime.now(timezone.utc).isoformat(), 'title': 'No recent news', 'summary': 'No recent news', 'link': '', 'source': self.sourceName, 'fetcher': self._getClassName(), 'id': f"{self._getClassName()}-norecent-{datetime.now().timestamp()}" }]

        # sort by published date, most recent first
        recentInfo.sort(key=self._getRecordDate, reverse=True)

        return recentInfo           
        

    def next(self)->dict:
        return self._vrotation.next()

    def asMessage(self, record:dict, panelSize:tuple[int,int]) -> Message:
        return Message("needs override")

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

    def _getCacheFilePath(self):
        className = self._getClassName()
        prefix = f"{className}_{self.sourceName}"
        file_name = AGGREGATE_CACHE_FILE_NAME.format(prefix)
        return Path(CACHE_DIR / file_name)

    def _fetchFromCache(self):
        aggregate_path = self._getCacheFilePath()
        info = []
        if aggregate_path.exists():
            try:
                info = json.loads(aggregate_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                logging.error(f"Error decoding JSON from cache for {aggregate_path}. Returning empty list.")
        else:
            logging.warning(f"No cache file found for {aggregate_path}. Returning empty list.")

        return info

    def _saveToCache(self, info):
        '''Save info to cache.'''

        info_existing = self._fetchFromCache()

        seen = set()
        deduped = []

        for record in info+info_existing:
            key = self._record_signature(record)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(record)

        aggregate_path = self._getCacheFilePath()
        aggregate_path.write_text(json.dumps(deduped, indent=2, ensure_ascii=False), encoding='utf-8')

    def _record_signature(self, record):
        signature = {
            'title': record.get('title', ''),
         #   'link': record.get('link', ''),
            'published': record.get('published', ''),
        }
        return hashlib.md5(json.dumps(signature, sort_keys=True).encode('utf-8')).hexdigest()

    @abstractmethod
    def _getRecordDate(self, record) -> datetime:
        '''return the date of the record as datetime object'''
        
    @abstractmethod
    def _prepare(self):
        '''Do initial prepration work, like openign communication with source and initiating chat'''

    @abstractmethod
    def _fetch(self)->list:
        '''fetch a batch of fresh info'''

class InfoFetcher_xAI(InfoFetcher):

    def __init__(self, API_key, model, promptInitial, PromptRefresh="Refresh please") -> None:
        super().__init__('xAI')
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

class NewsFetcher(InfoFetcher):

    _catalog = {}

    @staticmethod
    def find(item):

        catalog = NewsFetcher._catalog
        ns_members = NewsSource.__members__

        if item in NewsSource:
            news_name = item.name
        else:
            if item not in ns_members:
                logging.error(f"item '{item}' not in NewsSource")
                raise Exception()
            news_name = item
        
        # builde catalog
        if news_name not in catalog:
            url, timeZone = ns_members[news_name].value
            catalog[news_name] = NewsFetcher(url, news_name, timeZone)

        return catalog[news_name]

    
    def __init__(self, rss_url, sourceName, sourceTimeZone) -> None:

        super().__init__(sourceName=sourceName)
        self.rss_url = rss_url
        self.sourceTimeZone = sourceTimeZone

    def _prepare(self):
        pass

    def _fetch(self) -> list:

        def get_item_id(entry):
            """Create a unique ID for each news item"""
            return entry.get('link') or entry.get('id') or hashlib.md5(entry.title.encode()).hexdigest()
        
        # fetch request timestamp
        frt = datetime.now(timezone.utc)

        news = []

        try:
            feed = feedparser.parse(self.rss_url)
            
            if feed.bozo:  # Feed has parsing issues
                logging.warning("Feed parsing issues detected.")
            

            for news_entry in feed.entries:

                item_id = get_item_id(news_entry)
                

                # evaluate published date
                published_str = f"{news_entry.get('published', news_entry.get('updated', ''))}"

                try:
                    published = dateparser.parse(published_str)

                except (ValueError, TypeError) as e:
                    logging.error(f"Error parsing date '{published_str}': {e}")
                
                else:
                    
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
                        'published': convertDate2String(published),
                        'source': self.sourceName,
                        'fetcher': self._getClassName(),
                        'fetched_timestamp': convertDate2String(frt),
                        'id': item_id
                    }
                    news.append (record)
                
                
        except Exception as e:
            logging.error(f"Error fetching feed: {e}")
        
        return news

    def _getRecordDate(self, record):
        ts_str = record['published']
        return datetime.fromisoformat(ts_str)

    def asMessage(self, record, panelSize:tuple[int,int]) -> Message:
        source, title, summary, published, link = [record[field] for field in ('source', 'title', 'summary', 'published', 'link')]
        colWidth, rowCount = panelSize
        source = " " + source.replace("_", " ")
        
        dt_utc =  datetime.fromisoformat(published)
        dt_local = dt_utc.astimezone(pytz.timezone(LOCAL_TIME_ZONE))

        tstamp = f"{dt_local.strftime('%a %b').upper()} {dt_local.day} {dt_local.strftime('%H')}H{dt_local.strftime('%M')}"

        lines = ['' for _ in range(rowCount)]

        lines[0] = tstamp
        content=textwrap.wrap(title, width=colWidth)
        for i in range(len(content)):
            if i+2<rowCount:
                lines[i+2] = content[i]
        BottomLine = lines[-1][:colWidth-len(source)]
        m = colWidth-len(BottomLine)-len(source)
        lines[-1] = BottomLine+ " "*m + source
        solari= '<br>'.join(lines)

        return Message(text=solari, displayTime='30 seconds', link=link, fetcher=self)
    



''' tests '''

def testFetcher():
    pr0 = PROMPT_DIR / "news_gathering.txt"
    fetcher1 = InfoFetcher_xAI( os.getenv("XAI_API_KEY"), 
                                model="grok-4-1-fast-reasoning", 
                                promptInitial=pr0)
    fetcher1.setCacheUsageFlag(True)

    fetcher2 = NewsFetcher.find(NewsSource.AL_JAZEERA)
    
    fetcher2.start(interval=1, limit=2)

    while fetcher2.isrunning():
        record = fetcher2.next()
        if record:
            solariText = fetcher2.asMessage(record).text
            logging.info(f'SOLARI : {solariText} ')
        time.sleep(5)

    

    

if __name__ == "__main__":
    # test_TASSNewsFeed()
    # test_XAI_NewsFeed()
    testFetcher()