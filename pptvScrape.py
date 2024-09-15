import json
import re
from exceptiongroup import catch
import requests
import urllib.parse
from bs4 import BeautifulSoup as bs

xmlUrl = "https://www.pptvhd36.com/sitemap-2024-09-15.xml"
JSON_output = "data/pptv15092024"

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
}

def needsEncoding(s):
    return s[0] == "%" and s[3] == "%"

def CreateNewsElement(url):
    category = url.replace('https://www.pptvhd36.com/', '').split('/')
    if (needsEncoding(category[-2])):
        category = urllib.parse.unquote(category[-2])
    elif (category[-2] == "news"):
        category = category[-3]
    else:
        category = category[0]

    res = requests.get(url, headers = headers)
    soup = bs(res.text, 'html.parser')
    date = soup.find("time")
    if (date == None):
        date = "15 ก.ย. 2567"
    else:
        date = date.getText()

    content = soup.find("div", {"class": re.compile("content-details__body|sport_detail__body")})
    if (content == None): return

    data = content.select("p")[2:]
    data = " ".join(p.get_text(strip=True) for p in data)
    data = data.replace(",", " ")
    json_data = {"data": data, "category": category, "date": date, "publisher": "PPTV", "url": url}
    with open(JSON_output, 'a', encoding = "utf-8") as file:
        json.dump(json_data, file, ensure_ascii=False, indent=5)

res = requests.get(xmlUrl, headers = headers)

soup = bs(res.text, 'html.parser')
allURLsSoup = soup.find_all("url")
allURLs = []

for e in allURLsSoup:
    url = e.find("loc").text

    filter = url.replace('https://www.pptvhd36.com/', '').split('/')
    if ("programs" in filter or filter[0] == "video" or filter[0] == "tags" or filter[0] == "gallery"): continue

    allURLs.append(url)

for news in allURLs:
    try:
        CreateNewsElement(news)
    except (err):
        continue