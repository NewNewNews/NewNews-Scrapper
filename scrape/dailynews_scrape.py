import os
import requests
from bs4 import BeautifulSoup as bs
import json

central_categories = {
        'Sports': [
            'บุนเดสลีกา', 'ลาลีกา', 'พรีเมียร์ลีก', 'กีฬาไทย', 
            'มวยสากล', 'ทีมชาติไทย', 'ฟุตบอลทั่วไป', 'มวยไทย'
        ],
        'Entertainment': [
            'บันเทิง', 'Daily Beauty', 'นวัตกรรมขนส่ง'
        ],
        'Politics & Society': [
            'การเมือง', 'ประชาสัมพันธ์', 'สังคม', 'ต่างประเทศ'
        ],
        'Lifestyle & Culture': [
            'ท่องเที่ยว-ที่พัก', 'การศึกษา-ศาสนา', 'เศรษฐกิจ'
        ],
        'News & Current Affairs': [
            'เทคโนโลยี', 'อาชญากรรม', 'กทม.', 'ทั่วไทย', 'เกษตร'
        ]
    }

def ScrapeNews(n, url, newServices, date="", dev_mode = False):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            lastmod = e.find("lastmod").text if e.find("lastmod") else ""
            CallElement(loc, headers, newServices, dev_mode, lastmod)
            count += 1
        except Exception as e:
            print(f"Error with sitemap element: {e}")
            continue
        if count == n:
            break

def CallElement(url, headers, newServices, dev_mode, date=""):
    try:
        res = requests.get(url, headers=headers)
        soup = bs(res.text, "lxml")

        # Extract the category
        category = (
            soup.find("div", {"data-elementor-type": "single-post"})
            .find("nav", recursive=False)
            .find("div")
            .find("div")
        )
        category = category.find_all("a")[-1].text
        category = map_category(category)

        # Extract the content
        content = soup.find("main")
        if content is None:
            return

        data = content.select("p")
        data = " ".join(p.get_text(strip=True) for p in data)
        data = data.replace(",", " ")

        # Prepare the JSON data
        json_data = {
            "data": data,
            "category": category,
            "date": date,
            "publisher": "Dailynews",
            "url": url,
        }

        # Store in MongoDB
        if (not dev_mode):
            print(type(newServices))
            newServices.collection.insert_one(json_data)

            # Send to Kafka
            newServices.kafka_producer.send(
                "news_topic", json.dumps(json_data).encode("utf-8")
            )
        else:
            with open("../data_temp/dailynews_news_temp", 'a', encoding = "utf-8") as file:
                json.dump(json_data, file, ensure_ascii = False, indent = 5)

    except Exception as e:
        print(f"Error processing URL {url}: {e}")

def map_category(news_category):
    for central, categories in central_categories.items():
        if news_category in categories:
            return central
    return 'Etc'