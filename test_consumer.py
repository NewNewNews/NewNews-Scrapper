from kafka import KafkaConsumer
from proto import news_message_pb2

consumer = KafkaConsumer(
    "scraped-news",
    bootstrap_servers=["localhost:9092"],
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    # group_id="news-consumers",
)


def process_message(message):
    news_message = news_message_pb2.NewsMessage()
    news_message.ParseFromString(message.value)
    print(f"Received news: Category: {message.key.decode('utf-8')}")
    print(f"Data: {news_message.data}")
    print(f"Date: {news_message.date}")
    print(f"Publisher: {news_message.publisher}")
    print(f"URL: {news_message.url}")
    print("---")


for message in consumer:
    process_message(message)
