import os
import requests
from bs4 import BeautifulSoup as bs
import json
import json
from confluent_kafka import Producer, KafkaError
from confluent_kafka.serialization import (
    SerializationContext,
    MessageField,
)
from proto import news_message_pb2

central_categories = {
    "Sports": [
        "บุนเดสลีกา",
        "ลาลีกา",
        "พรีเมียร์ลีก",
        "กีฬาไทย",
        "มวยสากล",
        "ทีมชาติไทย",
        "ฟุตบอลทั่วไป",
        "มวยไทย",
    ],
    "Entertainment": ["บันเทิง", "Daily Beauty", "นวัตกรรมขนส่ง"],
    "Politics & Society": ["การเมือง", "ประชาสัมพันธ์", "สังคม", "ต่างประเทศ"],
    "Lifestyle & Culture": ["ท่องเที่ยว-ที่พัก", "การศึกษา-ศาสนา", "เศรษฐกิจ"],
    "News & Current Affairs": ["เทคโนโลยี", "อาชญากรรม", "กทม.", "ทั่วไทย", "เกษตร"],
}


def ScrapeNews(n, url, newServices, date="", dev_mode=False):
    query = {"publisher": "Dailynews"}
    existedUrls = newServices.collection.distinct("url", query)
    existedUrls = set(existedUrls)


    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "lxml-xml")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            lastmod = e.find("lastmod").text if e.find("lastmod") else ""
            if loc not in existedUrls:
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
        soup = bs(res.text, "lxml-xml")

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
        news_message = news_message_pb2.NewsMessage(
            data=json_data["data"],
            category=json_data["category"],
            date=json_data["date"],
            publisher=json_data["publisher"],
            url=json_data["url"],
        )

        # Store in MongoDB
        if not dev_mode:
            inserted_data = newServices.collection.insert_one(json_data)

            def delivery_report(err, msg, a):
                if err is not None:
                    print(f"Message delivery failed: {err}")
                else:
                    print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

            json_data["_id"] = str(inserted_data.inserted_id)

            topic = "news_topic"
            try:
                newServices.kafka_producer.produce(
                    topic=topic,
                    key=newServices.string_serializer(json_data["category"]),
                    value=newServices.protobuf_serializer(
                        news_message, SerializationContext(topic, MessageField.VALUE)
                    ),
                    on_delivery=newServices.delivery_report,
                )
                print("already send")
            except KafkaError as e:
                print(f"Failed to send message to Kafka: {e}")

        else:
            with open(
                "../data_temp/dailynews_news_temp", "a", encoding="utf-8"
            ) as file:
                json.dump(json_data, file, ensure_ascii=False, indent=5)

    except Exception as e:
        print(f"Error processing URL {url}: {e}")


def map_category(news_category):
    for central, categories in central_categories.items():
        if news_category in categories:
            return central
    return "Etc"
