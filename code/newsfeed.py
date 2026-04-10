from pathlib import Path
import schedule
from threading import Thread
import os
import feedparser
import time
import hashlib
import pytz
from datetime import datetime,timedelta, timezone
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

NEWS_CACHE_FILE_NAME_PREFIX = "news_cache"
NEWS_CACHE_FILE_NAME = f"{NEWS_CACHE_FILE_NAME_PREFIX}_{"{}"}.txt"

REFRESH_CYCLE = 30 # in minutes

LOCAL_TIME_ZONE = "US/Eastern"

class NewsFetcher(ABC):

    def run(self):
        news = self.fetch()
        self.save(news)
        return news

    @staticmethod
    def getNewsFromCache():
        root = CACHE_DIR
        pattern = NEWS_CACHE_FILE_NAME.format("2026*")
        paths = list(root.rglob(pattern))
        news =[]
        for path in paths:
            news.extend( json.load(open(path)))
        return news

    @abstractmethod
    def fetch(self)->list:
        '''fetch a batch of fresh news'''

    def save(self, news_JSON):
        '''Save news to cache '''

        # get timestamp
        now = datetime.now().strftime( "%Y.%m.%d %H:%M:%S")
        
        # save two files: with with name showing timestamp and one with name showing current
        for param in [now, 'current']:
            file_name = NEWS_CACHE_FILE_NAME.format(param)
            path = Path(CACHE_DIR / file_name)
            path.write_text(news_JSON)

class NewsFetcher_xAI(NewsFetcher):

    def __init__(self, API_key, model) -> None:
        super().__init__()

        os.environ["XAI_API_KEY"] = API_key  # Ensure the API key is set in environment variables

        # instantiate XAI Client
        client = xai.Client()

        # create XAI chat with web search and X search capabilities
        tools=[xai_tools.web_search(), xai_tools.x_search()]
        self.chat = client.chat.create(model=model, store_messages=True, tools=tools )

        # get initial prompt to prepare the news feed
        prompt = getPromt(NEWS_GATHERING_PROMPT)
        response = self.processPrompt(prompt)

        assert(response=="OK")

    def fetch(self) -> list:
        
        # obtain from XAI a new batch of news
        response = self.processPrompt("Please refresh")
        
        news =[]
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
                        'fetcher': 'XAI',
                        'fetch_timestamp': now,
                        'id': f"XAI-{now}{id}",
                            }
                news.append(item)
        return news
    
    def processPrompt(self, prompt)->str:
        '''Send a prompt to XAI API and return the response'''
        
        self.chat.append(xai_chat.user(prompt))
        response = self.chat.sample()
        self.chat.append(response)    

        return response.content

class NewsFetcher_TASS(NewsFetcher):

    def fetch(self) -> list:
        def get_item_id(entry):
            """Create a unique ID for each news item"""
            return entry.get('link') or entry.get('id') or hashlib.md5(entry.title.encode()).hexdigest()
        
        # fetch request timestamp
        frt = datetime.now()

        news = []

        try:
            feed = feedparser.parse(TASS_RSS_URL)
            
            if feed.bozo:  # Feed has parsing issues
                logging.warn("Feed parsing issues detected.")
            

            for news_entry in feed.entries:

                item_id = get_item_id(news_entry)
                

                # evaluate published date
                published = news_entry.get('published_parsed', news_entry.get('updated_parsed', None))

                if published:
                    year, month, day, hour, minute, second = [ published.__getattribute__(field) for field in ['tm_year', 'tm_mon', 'tm_mday', 'tm_hour', 'tm_min', 'tm_sec'] ]
                    published = datetime(year=year, month=month, day=day,
                                            hour=hour, minute=minute, second=second)
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
                    'published': published,
                    'source': 'TASS',
                    'fetcher': 'TASS',
                    'fetched_timestamp': frt,
                    'id': item_id
                }
                news.append (record)
            
                
        except Exception as e:
            logging.error(f"Error fetching feed: {e}")
        
        return news

class NewsFeed(ABC):

    def __init__(self, fetchers:list, refrechCycle , lastMinutes=24*60, maxItems=10, rotationCycle=15, useCacheOnly=False):
        '''
        refresh_cyle : time interval between getting fresh news (in minutes)
        rotationCycle : time interval between 2 news obtainted through the get method
        '''
        self.fetchers = fetchers
        self.refresh_cycle = refrechCycle
        self.lastMinutes=lastMinutes
        self.maxItems=maxItems
        self.rotationCycle = rotationCycle
        self.useCacheOnly = useCacheOnly
        self._news=[]
        self.startTimeStamp = datetime.now()
        self._start_scheduler(self._fetch_news)

    def get(self):
        result = None
        news = self._news
        newsCount = len (news)
        if newsCount > 0:
            seconds = (datetime.now() - self.startTimeStamp).seconds
            k = (seconds // self.refresh_cycle) % newsCount
            result = news[k]
        return result


    def _fetch_news(self):

        logging.info('_fetch_news invoked')

        if self.useCacheOnly:
            news = NewsFetcher.getNewsFromCache()
        else:
            news =[]
            for fetcher in self.fetchers:
                news.extend( fetcher.run())

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.lastMinutes)

        def datef(item):
            return datetime.strptime(item['published'], "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc) 


        news = [item for item in news if datef(item)>cutoff]

        news = sorted(news, key=lambda item:datef(item))

        news = news[-self.maxItems:]

        self._news = news

    def _start_scheduler(self, targetFunction):
        self.running = True

        # start targetFunction immediately
        targetFunction()

        # schedule calls to targetFunction every refresh_cycle
        schedule.every(self.refresh_cycle).minutes.do(targetFunction)
        
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(1)
            logging.info("scheduler stopped")
        
        thread = Thread(target=run_scheduler, daemon=True)
        thread.start()
        logging.info("scheduler started")
    
    def stop(self):
        self.running = False

''' Helper function'''

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

def testFeeder():
    fetcher1 = NewsFetcher_xAI(os.getenv("XAI_API_KEY"), model="grok-4-1-fast-reasoning")
    fetcher2 = NewsFetcher_TASS()
    feed=NewsFeed( [fetcher1, fetcher2], refrechCycle=3, useCacheOnly=True)
    news_id = ''
    while True:
        news = feed.get()
        if news:
            if news['id'] != news_id:
                logging.info(f"news : {news['title']} - {news['summary']}")
                news_id = news['id']


def testFetcher():
    news = NewsFetcher.getNewsFromCache()
    

if __name__ == "__main__":
    # test_TASSNewsFeed()
    # test_XAI_NewsFeed()
    testFeeder()