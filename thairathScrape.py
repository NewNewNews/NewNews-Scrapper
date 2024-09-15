import json
import re
import requests
from bs4 import BeautifulSoup as bs

xmlUrl = "https://www.thairath.co.th/sitemap-daily.xml"
JSON_output = "data/thairath14092024"

def CreateNewsElement(url):
    category = url.split("/")[3:]
    if (category[0] == "news"):
        category = category[1]
    else:
        category = category[0]

    res = requests.get(url)
    soup = bs(res.text, 'html.parser')
    date = soup.find("div", class_=re.compile(r"__item_article-date.*\bcss\b"))
    if (date == None):
        date = "14 ก.ย. 2567"
    else:
        date = date.getText()

    content = soup.find("div", {"itemprop": "article-body"})
    if (content == None): content = soup.find("div", {"itemprop": "articleBody"})
    if (content == None): return
    data = content.select("p")
    data = " ".join(p.get_text(strip=True) for p in data)
    data = data.replace(",", " ")
    json_data = {"data": data, "category": category, "date": date, "publisher": "Thairath", "url": url}
    with open(JSON_output, 'a', encoding = "utf-8") as file:
        json.dump(json_data, file, ensure_ascii=False, indent=5)

res = requests.get(xmlUrl)
soup = bs(res.text, 'html.parser')
allURLsSoup = soup.find_all("url")
allURLs = []

for e in allURLsSoup:
    allURLs.append(e.find("loc").text)

for news in allURLs:
    CreateNewsElement(news)