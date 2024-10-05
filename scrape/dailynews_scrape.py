import requests
from bs4 import BeautifulSoup as bs
import json

def ScrapeNews(n, url, newServices, date=""):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            lastmod = e.find("lastmod").text if e.find("lastmod") else ""
            CallElement(loc, headers, newServices, lastmod)
            count += 1
        except Exception as e:
            print(f"Error with sitemap element: {e}")
            continue
        if count == n:
            break

def CallElement(url, headers, newServices, date=""):
    try:
        res = requests.get(url, headers=headers)
        soup = bs(res.text, "html.parser")

        # Extract the category
        category = (
            soup.find("div", {"data-elementor-type": "single-post"})
            .find("nav", recursive=False)
            .find("div")
            .find("div")
        )
        category = category.find_all("a")[-1].text

        # Extract the content
        content = soup.find("main")
        if content is None:
            return

        data = content.select("p")
        data = " ".join(p.get_text(strip=True) for p in data)
        data = data.replace(",", " ")
        print(f"this is data {data}")
        # Prepare the JSON data
        json_data = {
            "data": data,
            "category": category,
            "date": date,
            "publisher": "Dailynews",
            "url": url,
        }

        # Store in MongoDB
        newServices.collection.insert_one(json_data)

        # Send to Kafka
        newServices.kafka_producer.send(
            "news_topic", json.dumps(json_data).encode("utf-8")
        )

    except Exception as e:
        print(f"Error processing URL {url}: {e}")