import feedparser
import time
import hashlib
from datetime import datetime
from abc import ABC, abstractmethod

# TASS RSS feed URL 
# RSS_URL = "https://tass.com/rss/v2.xml"
RSS_URL = "https://www.themoscowtimes.com/rss/news"
# RSS_URL = "https://apnews.com/index.rss"

# Track seen items by their unique link (or GUID if available)

class NewsFeed(ABC):
    
    news = {}

    def __init__(self, RSS_URL):
        self.RSS_URL = RSS_URL
    
    @abstractmethod
    def fetch_news(self):
        ''''''

    def get_news(self, lastMinutes=24*60, maxItems=10):
        '''Return a list of news items fetched within the last `lastMinutes` minutes, limited to `maxItems` items.'''
        newsList = [v for v in self.news.values() if (datetime.now() - v['published']).total_seconds() < lastMinutes * 60]
        shortNewsList=sorted(newsList, key=lambda x: x['published'], reverse=True)[:maxItems]
        return shortNewsList

class TASSNewsFeed(NewsFeed):
    
    def fetch_news(self):

        def get_item_id(entry):
            """Create a unique ID for each news item"""
            return entry.get('link') or entry.get('id') or hashlib.md5(entry.title.encode()).hexdigest()
        
        # fetch request timestamp
        frt = datetime.now()

        try:
            feed = feedparser.parse(self.RSS_URL)
            
            if feed.bozo:  # Feed has parsing issues
                print("Warning: Feed parsing issues detected.")
            
            for news_entry in feed.entries:

                item_id = get_item_id(news_entry)
                
                if item_id not in self.news:

                    # evaluate published date
                    published = news_entry.get('published_parsed', news_entry.get('updated_parsed', None))
                    if published:
                        published = datetime(year=published.tm_year, month=published.tm_mon, day=published.tm_mday,
                                             hour=published.tm_hour, minute=published.tm_min, second=published.tm_sec)
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
                        'link': news_entry.link,
                        'published': published,
                        'summary': summary,
                        'fetched at': frt,
                    }
                    self.news[item_id] = record                    
            
            return True
            
                
        except Exception as e:
            print(f"Error fetching feed: {e}")
            return False

if __name__ == "__main__":
    print("Starting TASS RSS real-time monitor (Ctrl+C to stop)\n")
    
    tass = TASSNewsFeed(RSS_URL)

    while True:
        tass.fetch_news()
        news = tass.get_news()
        for news_item in news:
            print(f"{news_item['published']} - {news_item['title']}")        
        print("\n---\n")
        time.sleep(60)