import requests
from bs4 import BeautifulSoup as bs
import json
import re
from datetime import date

def ScrapeNews(n, url, newServices, date=""):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            CallElement(loc, headers, newServices)
            count += 1
        except Exception as e:
            print(f"Error with sitemap element: {e}")
            continue
        if count == n:
            break

def CallElement(url, headers, newServices, date=""):
    category = url.split("/")[3:]
    if (category[0] == "news"):
        category = category[1]
    else:
        category = category[0]

    res = requests.get(url)
    soup = bs(res.text, 'html.parser')
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
    
    # Store in MongoDB
    newServices.collection.insert_one(json_data)

    # Send to Kafka
    newServices.kafka_producer.send(
        "news_topic", json.dumps(json_data).encode("utf-8")
    )

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