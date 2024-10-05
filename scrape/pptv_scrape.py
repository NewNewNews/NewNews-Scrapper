import requests
from bs4 import BeautifulSoup as bs
import json
import re
import urllib.parse
from datetime import date

def ScrapeNews(n, url, newServices, date=""):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")

    allURLsSoup = soup.select("url")
    allURLs = []

    for e in allURLsSoup:
        url = e.find("loc").text

        filter = url.replace("https://www.pptvhd36.com/", "").split("/")
        if (
            "programs" in filter
            or filter[0] == "video"
            or filter[0] == "tags"
            or filter[0] == "gallery"
        ):
            continue

        allURLs.append(url)

    count = 0
    for e in allURLs:
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
    category = url.replace("https://www.pptvhd36.com/", "").split("/")
    if needsEncoding(category[-2]):
        category = urllib.parse.unquote(category[-2])
    elif category[-2] == "news":
        category = category[-3]
    else:
        category = category[0]

    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")
    date = soup.find("time")
    if date == None:
        date = getDate()
    else:
        date = date.getText()

    content = soup.find(
        "div", {"class": re.compile("content-details__body|sport_detail__body")}
    )
    if content == None:
        return

    data = content.select("p")[2:]
    data = " ".join(p.get_text(strip=True) for p in data)
    data = data.replace(",", " ")
    json_data = {
        "data": data,
        "category": category,
        "date": date,
        "publisher": "PPTV",
        "url": url,
    }

    newServices.collection.insert_one(json_data)

    # Send to Kafka
    newServices.kafka_producer.send(
        "news_topic", json.dumps(json_data).encode("utf-8")
    )

def needsEncoding(s):
    return s[0] == "%" and s[3] == "%"

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