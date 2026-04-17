from enum import Enum
from pathlib import Path
import os
import feedparser
import time
import hashlib
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from abc import ABC, abstractmethod
from common import CACHE_DIR, PROMPT_DIR, Helper, convertDate2String, ValueRotation, Scheduler, getPrompt
import json

import xai_sdk as xai
import xai_sdk.chat as xai_chat
import xai_sdk.tools as xai_tools

from common import time_to_seconds, Message

from dotenv import load_dotenv
load_dotenv()

logger = Helper.supplyLogger()


XAI_NEWS_RSS_URL = "https://api.x.ai/v1"  # Placeholder URL for XAI news feed

XAI_NEWS_GATHERING_PROMPT = "news_gathering.txt"

NEWS_CACHE_FILE_NAME_PREFIX = "cache_info"
AGGREGATE_CACHE_FILE_NAME = NEWS_CACHE_FILE_NAME_PREFIX + "_{}_aggregate.txt"
class InfoSource(Enum):
    DW= {'fetcherClass':'NewsFetcher', 'rss_url':"https://rss.dw.com/rdf/rss-en-world", 'sourceTimeZone':"Europe/Berlin"}
    ZEROHEDGE= {'fetcherClass':'NewsFetcher', 'rss_url':"https://cms.zerohedge.com/fullrss2.xml", 'sourceTimeZone':"US/Eastern", 'fetchInterval':'4 minutes'}
    NHK_WORD= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www3.nhk.or.jp/nhkworld/data/en/news/backstory/rss.xml", 'sourceTimeZone':"Asia/Tokyo"}
    GLOBO= {'fetcherClass':'NewsFetcher', 'rss_url':"https://g1.globo.com/rss/g1/mundo/", 'sourceTimeZone':"America/Sao_Paulo"}
    VATICAN_NEWS= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.vaticannews.va/en.rss.xml", 'sourceTimeZone':"Europe/Vatican"}
    LA_CROIX= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.la-croix.com/feeds/rss/site.xml", 'sourceTimeZone':"Europe/Paris"}
    NY_TIMES= {'fetcherClass':'NewsFetcher', 'rss_url':"https://rss.nytimes.com/services/xml/rss/nyt/World.xml", 'sourceTimeZone':"US/Eastern", 'fetchInterval':'4 minutes 30 secondes'}
    CGTN= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.cgtn.com/subscribe/rss/section/world.xml", 'sourceTimeZone':"Asia/Shanghai"}
    FRANCE_24= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.france24.com/en/rss", 'sourceTimeZone':"Europe/Paris", 'fetchInterval':'5 minutes'}
    TIME_OF_INDIA= {'fetcherClass':'NewsFetcher', 'rss_url':"https://timesofindia.indiatimes.com/rssfeedstopstories.cms", 'sourceTimeZone':"Asia/Kolkata"}
    BBC= {'fetcherClass':'NewsFetcher', 'rss_url':"http://feeds.bbci.co.uk/news/rss.xml", 'sourceTimeZone':"Europe/London"}
    AL_JAZEERA= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.aljazeera.com/xml/rss/all.xml", 'sourceTimeZone':"Asia/Qatar"}
    TASS= {'fetcherClass':'NewsFetcher', 'rss_url':"https://tass.com/rss/v2.xml", 'sourceTimeZone':"Europe/Moscow"}
    INTERFAX= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.interfax.ru/rss.asp", 'sourceTimeZone':"Europe/Moscow"}
    THE_GUARDIAN= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.theguardian.com/world/rss", 'sourceTimeZone':"Europe/London"}
    PR_NEWSWIRE= {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.prnewswire.com/rss/news-releases-list.rss", 'sourceTimeZone':"US/Eastern"}   
    AP_NEWS= {'fetcherClass':'NewsFetcher', 'rss_url':"https://apnews.com/index.rss", 'sourceTimeZone':"US/Eastern"}
    MOSCOW_TIME = {'fetcherClass':'NewsFetcher', 'rss_url':"https://www.themoscowtimes.com/rss/news", 'sourceTimeZone':"Europe/Moscow"}

    XAI_NEWS_AGENT= {
        'fetcherClass':'InfoFetcher_xAI', 
        'API_key': os.getenv("XAI_API_KEY"), 
        'model':"grok-4-1-fast-reasoning", 
        'prompt': getPrompt(XAI_NEWS_GATHERING_PROMPT),
        'fetchInterval':'15 minutes' 
        }






class InfoFetcher(ABC):
    '''An InfoFetcher is a class that fetches information from a source and provides it in a format that can be displayed on the panel. The information is defined as a list of records, where each record is a dictionary that contains the information to display. The InfoFetcher class provides methods to fetch the information, to get the most recent information, to convert a record to a message that can be displayed on the panel, and to manage the cache of the fetched information. The InfoFetcher class is an abstract class that needs to be subclassed to implement the specific fetching logic for each source of information. The subclass needs to implement the _fetch method that fetches the information from the source and returns it as a list of records, and the _getRecordDate method that returns the date of a record as a datetime object. The InfoFetcher class also provides a start method that schedules regular fetching of the information at a specified interval, and a stop method that stops the scheduled fetching.'''

    _catalog = {}

    @staticmethod
    def find(item):
        '''Find an InfoFetcher for the given item. The item can be an InfoSource enum member or a string that matches the name of an InfoSource enum member. The method returns an instance of the InfoFetcher subclass that corresponds to the item. The method uses a catalog to cache the created InfoFetcher instances, so that if the same item is requested again, the cached instance is returned instead of creating a new one. If the item is not found in the InfoSource enum, an exception is raised.
        '''
        catalog = InfoFetcher._catalog
        is_members = InfoSource.__members__

        if item in InfoSource:
            info_name = item.name
            
        else:
            if item not in is_members:
                logger.error(f"item '{item}' not in InfoSource")
                raise Exception()
            info_name = item
        
        # builde catalog
        if info_name not in catalog:
            params = is_members[info_name].value
            fetcherClass=globals().get(params['fetcherClass'])
            if fetcherClass is None:
                logger.error(f"fetcherClass '{params['fetcherClass']}' not found in globals")
                raise Exception()
            catalog[info_name] = fetcherClass(sourceName=info_name, **params)

        return catalog[info_name]

    def __init__(self, sourceName, fetchInterval="10 minutes", timeWindow= '24 hours', **kwargs) -> None:
        '''
        sourceName:     name of the source of information, e.g. "DW", "BBC", "XAI_NEWS_AGENT"
        fetchInterval:  interval in minutes between two fetches of information. The fetch method is called at
                        regular intervals defined by fetchInterval, which is used to update the information displayed 
                        on the panel.
        timeWindow:     time window for considering information as recent. The mostRecentInfo method uses 
                        the timeWindow to filter the fetched information and to determine which informationisconsidered 
                        recent and should be displayed on the panel.
        '''

        super().__init__()
        self.setCacheUsageFlag(False)
        self.sourceName = sourceName
        self._started = False
        self._scheduler = None
        self.fetchIntervalMinutes = time_to_seconds(fetchInterval) // 60
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
            logger.warning(f"No recent info found for {self.sourceName}")
            recentInfo = [{'published': datetime.now(timezone.utc).isoformat(), 'news': 'Loading feed...',  'link': None, 'source': self.sourceName, 'fetcher': self._getClassName(), 'id': f"{self._getClassName()}-norecent-{datetime.now().timestamp()}" }]

        # sort by published date, most recent first
        recentInfo.sort(key=self._getRecordDate, reverse=True)

        return recentInfo           
        

    def next(self)->dict:
        return self._vrotation.next()


    def setCacheUsageFlag(self, flag):
        self._useCache = flag in [True,'on', 'ON']

    def _getClassName(self):
        return self.__class__.__name__

    def start(self, limit = None):
        '''schedule regular info fetching'''
        self._scheduler = Scheduler(self.fetch , interval=self.fetchIntervalMinutes, limit=limit)
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
                logger.error(f"Error decoding JSON from cache for {aggregate_path}. Returning empty list.")
        else:
            logger.warning(f"No cache file found for {aggregate_path}. Returning empty list.")

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

    ''' ABSTRACT METHODS '''

    @abstractmethod
    def _getRecordDate(self, record) -> datetime:
        '''return the date of the record as datetime object'''
        
    @abstractmethod
    def recordAsSolariMessage(self, record:dict, panelSize:tuple[int,int]) -> Message:
        '''Convert a record to a Message that can be displayed on the panel. The method takes a record as input and returns a Message object that contains the text to display on the panel, the time to display the message, and an optional link. The method needs to be overloaded in the subclass to implement the specific logic for converting a record to a Message for each source of information. The default implementation returns a Message with the class name and a note that the asMessage method needs to be overloaded.'''

    @abstractmethod
    def _prepare(self):
        '''Do initial prepration work, like openign communication with source and initiating chat'''

    @abstractmethod
    def _fetch(self)->list:
        '''fetch a batch of fresh info'''

class InfoFetcher_xAI(InfoFetcher):

    def __init__(self, API_key, model, prompt, **kwargs) -> None:
        super().__init__(**kwargs)
        self.API_key = API_key
        self.model = model
        self.prompt = prompt

    def _prepare(self):


        try:

            # send initial prompt to prepare the news feed and check response
            response = self.processPrompt("Hello! Just repond 'OK' to confirm you are here and ready. Thanks! " )
            assert(response=="OK")

        except Exception as e:
            logger.error(f"Error during initial preparation of {self.__class__.__name__}: {e}")

    def _fetch(self) -> list:
        
        # obtain from XAI a new batch of news
        response = self.processPrompt(self.prompt)
        
        info =[]
        now = datetime.now().isoformat()

        if response:
            try:
                news_recs = json.loads(response)
                for news_rec in news_recs:
                    try:
                        news, news_orig, source, published, link, id=[news_rec[field] for field in  ( "news", "news_orig","source","published","link","id")]

                        item = {
                                'news': news,
                                'news_orig': news_orig,
                                'link': link,
                                'published': published,
                                'source': source+ "/XAI",
                                'model': self.model,
                                'fetcher': self._getClassName(),
                                'fetched': now,
                                'id': f"XAI-{now}{id}",
                                    }
                        info.append(item)
                    except KeyError as e:
                        logger.error(f"Missing expected field in XAI response: {e}. Record was: {news_rec}")
                logger.info(f"Fetched {len(info)} news items from {self.sourceName}")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response from XAI: {e}. Response was: {response}")
        return info
    
    def _getRecordDate(self, record):
        ts_str = record['published']
        return datetime.fromisoformat(ts_str)

    def processPrompt(self, prompt)->str:

        t_i = datetime.now()

        response = self._processPrompt(prompt)

        t_f = datetime.now()

        resp_clean = response.replace("\r","").replace("\n","")

        logger.info(f"XAI prompt ({len(prompt)} characters) responded in {(t_f - t_i).total_seconds():0} seconds :  {resp_clean[:20]}... ({len(resp_clean)} characters)")

        return response

    def _processPrompt(self, prompt)->str:
        '''Send a prompt to XAI API and return the response'''
                    # retrieve self.API_key from environment variables and set it for the XAI client

        # instantiate XAI Client
        client = xai.Client(api_key=self.API_key)

        # create XAI chat with web search and X search capabilities
        tools=[xai_tools.web_search(), xai_tools.x_search()]
        chat = client.chat.create(model=self.model, store_messages=True, tools=tools, max_tokens=10000)

        chat.append(xai_chat.user(prompt))
        response = chat.sample()
        
        return response.content

    def recordAsSolariMessage(self, record: dict, panelSize: tuple[int, int]) -> Message:
        news, source, published, link = [record[field] for field in ('news', 'source', 'published', 'link')]
        
        dt_utc =  datetime.fromisoformat(published)

        content = news

        return Message.create(dt_utc, content, source, displayTime='30 seconds', link=link, panelSize=panelSize)
class NewsFetcher(InfoFetcher):

    
    def __init__(self, rss_url, sourceName, sourceTimeZone, **params) -> None:

        super().__init__(sourceName=sourceName, **params)
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
                logger.warning(f"Feed parsing issues detected for {self.sourceName}.")
            

            for news_entry in feed.entries:

                item_id = get_item_id(news_entry)
                

                # evaluate published date
                published_str = f"{news_entry.get('published', news_entry.get('updated', ''))}"

                try:
                    published = dateparser.parse(published_str)

                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing date '{published_str}': {e}")
                
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
                        'fetched': convertDate2String(frt),
                        'id': item_id
                    }
                    news.append (record)
            logger.info(f"Fetched {len(news)} news items from {self.sourceName}")
                
        except Exception as e:
            logger.error(f"Error fetching feed: {e}")
        
        return news

    def _getRecordDate(self, record):
        ts_str = record['published']
        return datetime.fromisoformat(ts_str)

    def recordAsSolariMessage(self, record, panelSize:tuple[int,int]) -> Message:
        source, title, published, link = [record[field] for field in ('source', 'title', 'published', 'link')]
        
        dt_utc =  datetime.fromisoformat(published)

        return Message.create(dt_utc, title, source, displayTime='30 seconds', link=link, panelSize=panelSize)
    



''' tests '''

def testFetcher():
    pr0 = PROMPT_DIR / "news_gathering.txt"
    fetcher1 = InfoFetcher_xAI( os.getenv("XAI_API_KEY"), 
                                model="grok-4-1-fast-reasoning", 
                                prompt=pr0)
    fetcher1.setCacheUsageFlag(True)

    fetcher2 = NewsFetcher.find(InfoSource.AL_JAZEERA)
    
    fetcher2.start(interval=1, limit=2)

    while fetcher2.isrunning():
        record = fetcher2.next()
        if record:
            solariText = fetcher2.asMessage(record).text
            logger.info(f'SOLARI : {solariText} ')
        time.sleep(5)

    

    

if __name__ == "__main__":
    # test_TASSNewsFeed()
    # test_XAI_NewsFeed()
    testFetcher()