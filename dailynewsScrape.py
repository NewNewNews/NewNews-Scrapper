import json
import re
import requests
from bs4 import BeautifulSoup as bs

xmlUrl = "https://www.dailynews.co.th/news-sitemap238.xml"
JSON_output = "data/dailynews238"

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"
}

def CreateNewsElement(url, date = ""):
    res = requests.get(url, headers= headers)
    soup = bs(res.text, 'html.parser')

    category = soup.find("div", {"data-elementor-type": "single-post"}).find("nav", recursive = False).find("div").find("div")
    category = category.find_all("a")[-1].text

    content = soup.find("main")
    if (content == None): return
    data = content.select("p")
    data = " ".join(p.get_text(strip=True) for p in data)
    data = data.replace(",", " ")
    json_data = {"data": data, "category": category, "date": date, "publisher": "Dailynews", "url": url}
    with open(JSON_output, 'a', encoding = "utf-8") as file:
        json.dump(json_data, file, ensure_ascii=False, indent=5)

res = requests.get(xmlUrl, headers = headers)
soup = bs(res.text, 'html.parser')
allURLsSoup = soup.select("url")

for e in allURLsSoup:
    try:
        CreateNewsElement(e.find("loc").text, e.find("lastmod").text)
    except:
        continue