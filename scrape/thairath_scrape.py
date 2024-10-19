import os
import requests
from bs4 import BeautifulSoup as bs
import json
import re
from datetime import date


import json
from confluent_kafka import Producer, KafkaError
from confluent_kafka.serialization import (
    SerializationContext,
    MessageField,
)
from proto import news_message_pb2

central_categories = {
    "Sports": ["sport"],
    "Entertainment": ["lifestyle", "entertain"],
    "Politics & Society": ["society", "politic", "crime"],
    "Lifestyle & Culture": ["local", "novel"],
    "News & Current Affairs": ["foreign", "scoop", "auto"],
}


def ScrapeNews(n, url, newServices, date="", dev_mode=False):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "lxml")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            if CallElement(loc, headers, newServices, dev_mode):
                count += 1
        except Exception as e:
            print(f"Error with sitemap element: {e}")
            continue
        if count == n:
            break


def CallElement(url, headers, newServices, dev_mode, date=""):
    category = url.split("/")[3:]
    if category[0] == "news":
        category = category[1]
    else:
        category = category[0]
    category = map_category(category)

    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")
    date = soup.find("div", class_=re.compile(r"__item_article-date.*\bcss\b"))
    if (date == None):
        date = convert_thai_date_to_iso(getDate())
    else:
        date = convert_thai_date_to_iso(date.getText())

    content = soup.find("div", {"itemprop": "article-body"})
    if content == None:
        content = soup.find("div", {"itemprop": "articleBody"})
    if content == None:
        return False

    data = content.select("p")
    data = " ".join(p.get_text(strip=True) for p in data)
    data = data.replace(",", " ")
    json_data = {
        "data": data,
        "category": category,
        "date": date,
        "publisher": "Thairath",
        "url": url,
    }
    news_message = news_message_pb2.NewsMessage(
        data=json_data["data"],
        category=json_data["category"],
        date=json_data["date"],
        publisher=json_data["publisher"],
        url=json_data["url"],
    )

    if not dev_mode:
        inserted_data = newServices.collection.insert_one(json_data)

        def delivery_report(err, msg):
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

        return True

    else:
        with open("../data_temp/thairath_news_temp", "a", encoding="utf-8") as file:
            json.dump(json_data, file, ensure_ascii=False, indent=5)


def getDate():
    thai_months = {
        1: "ม.ค.",
        2: "ก.พ.",
        3: "มี.ค.",
        4: "เม.ย.",
        5: "พ.ค.",
        6: "มิ.ย.",
        7: "ก.ค.",
        8: "ส.ค.",
        9: "ก.ย.",
        10: "ต.ค.",
        11: "พ.ย.",
        12: "ธ.ค.",
    }
    today = date.today()
    thai_year = today.year + 543
    thai_month = thai_months[today.month]
    formatted_thai_date = f"{today.day} {thai_month} {thai_year}"
    return formatted_thai_date


def convert_thai_date_to_iso(thai_date: str) -> str:
    thai_months = {
        "ม.ค.": "01", "ก.พ.": "02", "มี.ค.": "03", "เม.ย.": "04",
        "พ.ค.": "05", "มิ.ย.": "06", "ก.ค.": "07", "ส.ค.": "08",
        "ก.ย.": "09", "ต.ค.": "10", "พ.ย.": "11", "ธ.ค.": "12"
    }
    
    # Split the date into parts
    day, month_str, year_str = thai_date.split(" ")
    year = str(int(year_str) - 543)  # Convert from Buddhist year to Gregorian year
    month = thai_months[month_str]  # Get the month number

    # Combine into ISO format
    formatted_date = f"{year}-{month}-{day}"
    
    return formatted_date

def formatDate(input_date):
    thai_months = {
        "ม.ค.": "01", "ก.พ.": "02", "มี.ค.": "03", "เม.ย.": "04", 
        "พ.ค.": "05", "มิ.ย.": "06", "ก.ค.": "07", "ส.ค.": "08", 
        "ก.ย.": "09", "ต.ค.": "10", "พ.ย.": "11", "ธ.ค.": "12"
    }

    if "น." in input_date:
        date_part, time_part, remove = input_date.rsplit(" ", 2)
        time_part = time_part.replace(" น.", "")
    else:
        date_part = input_date
        time_part = "00:00"
    
    day, month_thai, buddhist_year = date_part.split()
    gregorian_year = int(buddhist_year) - 543
    month = thai_months[month_thai]
    date_time_str = f"{gregorian_year}-{month}-{day} {time_part}"
    dt = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
    iso_format = dt.isoformat() + "+00:00"

    return iso_format


def map_category(news_category):
    for central, categories in central_categories.items():
        if news_category in categories:
            return central
    return "Etc"
