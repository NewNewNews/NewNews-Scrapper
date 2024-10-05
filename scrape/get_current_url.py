import requests
from bs4 import BeautifulSoup as bs
import json
import re
import urllib.parse
from datetime import datetime

headers = {"User-Agent": "Mozilla/5.0"}

def getCurrentDailynews():
    head_url = "https://www.dailynews.co.th/sitemap_index.xml"
    res = requests.get(head_url, headers=headers)
    soup = bs(res.text, "html.parser")

    urls = soup.find("tbody").select("tr")[3:]
    number = find_xitemap(urls)

    return "https://www.dailynews.co.th/article-sitemap" + number + ".xml"

def getCurrentThairath():
    return "https://www.thairath.co.th/sitemap-daily.xml"

def getCurrentPPTV():
    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y-%m-%d")
    return "https://www.pptvhd36.com/sitemap-" + formatted_date + ".xml"


def find_xitemap(urls):
    highest_num = -1

    for url in urls:
        # Use regular expression to match elements that start with 'a' followed by a number
        match = re.search(r'article-sitemap(\d+)\.xml', url)
        if match:
            # Extract the number and compare with the current highest
            num = int(match.group(1))
            if num > highest_num:
                highest_num = num

    return highest_num