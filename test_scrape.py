import os
from bs4 import BeautifulSoup as bs
import json
from scrape import dailynews_scrape, pptv_scrape, thairath_scrape, get_current_url

headers = {"User-Agent": "Mozilla/5.0"}

def test_current_url():
    dailynews_url = get_current_url.getCurrentDailynews()
    pptv_url = get_current_url.getCurrentPPTV()
    thairath_url = get_current_url.getCurrentThairath()
    print(f"Current dailynew url: {dailynews_url}")
    print(f"Current pptv url: {pptv_url}")
    print(f"Current thairath url: {thairath_url}")
    return [dailynews_url, pptv_url, thairath_url]

def test_dailynews(url):
    os.makedirs(os.path.dirname("data/dailynews_news_temp"), exist_ok=True)
    dailynews_scrape.ScrapeNews(-1, url, "", "", True)

def test_pptv(url):
    os.makedirs(os.path.dirname("data/pptv_news_temp"), exist_ok=True)
    pptv_scrape.ScrapeNews(-1, url, "", "", True)

def test_thairath(url):
    os.makedirs(os.path.dirname("data/thairath_news_temp"), exist_ok=True)
    thairath_scrape.ScrapeNews(-1, url, "", "", True)

if __name__ == "__main__":
    urls = test_current_url()
    #test_dailynews(urls[0])
    #test_pptv(urls[1])
    test_thairath(urls[2])