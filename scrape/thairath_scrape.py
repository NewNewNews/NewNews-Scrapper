import os
import requests
from bs4 import BeautifulSoup as bs
import json
import re
from datetime import date

central_categories = {
        'Sports': ['sport'],
        'Entertainment': ['lifestyle', 'entertain'],
        'Politics & Society': ['society', 'politic', 'crime'],
        'Lifestyle & Culture': ['local', 'novel'],
        'News & Current Affairs': ['foreign', 'scoop', 'auto']
    }

def ScrapeNews(n, url, newServices, date="", dev_mode = False):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "lxml")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            CallElement(loc, headers, newServices, dev_mode)
            count += 1
        except Exception as e:
            print(f"Error with sitemap element: {e}")
            continue
        if count == n:
            break

def CallElement(url, headers, newServices, dev_mode, date=""):
    category = url.split("/")[3:]
    if (category[0] == "news"):
        category = category[1]
    else:
        category = category[0]
    category = map_category(category)

    res = requests.get(url)
    soup = bs(res.text, 'lxml')
    date = soup.find("div", class_=re.compile(r"__item_article-date.*\bcss\b"))
    if (date == None):
        date = getDate()
    else:
        date = date.getText()

    content = soup.find("div", {"itemprop": "article-body"})
    if (content == None): content = soup.find("div", {"itemprop": "articleBody"})
    if (content == None): return
    data = content.select("p")
    data = " ".join(p.get_text(strip=True) for p in data)
    data = data.replace(",", " ")
    json_data = {"data": data, "category": category, "date": date, "publisher": "Thairath", "url": url}

    if (not dev_mode):
        # Store in MongoDB
        newServices.collection.insert_one(json_data)

        # Send to Kafka
        newServices.kafka_producer.send(
            "news_topic", json.dumps(json_data).encode("utf-8")
        )
    else:
        with open("../data_temp/thairath_news_temp", 'a', encoding = "utf-8") as file:
                json.dump(json_data, file, ensure_ascii = False, indent = 5)

def getDate():
    thai_months = {
    1: "ม.ค.", 2: "ก.พ.", 3: "มี.ค.", 4: "เม.ย.", 5: "พ.ค.", 6: "มิ.ย.",
    7: "ก.ค.", 8: "ส.ค.", 9: "ก.ย.", 10: "ต.ค.", 11: "พ.ย.", 12: "ธ.ค."
    }
    today = date.today()
    thai_year = today.year + 543
    thai_month = thai_months[today.month]
    formatted_thai_date = f"{today.day} {thai_month} {thai_year}"
    return formatted_thai_date

def map_category(news_category):
    for central, categories in central_categories.items():
        if news_category in categories:
            return central
    return 'Etc'