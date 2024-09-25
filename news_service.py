import grpc
import requests
from bs4 import BeautifulSoup as bs
from concurrent import futures
import json
from pymongo import MongoClient
from proto import news_service_pb2
from proto import news_service_pb2_grpc
import os
from bson.objectid import ObjectId
from concurrent import futures
import grpc
from proto import news_message_pb2
import json
from confluent_kafka import Producer, KafkaError
from confluent_kafka.serialization import (
    StringSerializer,
    SerializationContext,
    MessageField,
)

from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.protobuf import ProtobufSerializer
from proto import news_message_pb2


class NewsService(news_service_pb2_grpc.NewsServiceServicer):
    def __init__(self):
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        kafka_broker = os.environ.get("KAFKA_BROKER", "localhost:9092")
        schema_registry_url = os.environ.get(
            "SCHEMA_REGISTRY_URL", "http://localhost:8081"
        )
        self.mongo_client = MongoClient(mongo_uri)  # mongodb://mongodb:27017/
        self.db = self.mongo_client["news_db"]
        self.collection = self.db["news"]
        print(f"connect success on port: {mongo_uri}")

        producer_conf = {"bootstrap.servers": kafka_broker}
        self.kafka_producer = Producer(producer_conf)
        schema_registry_conf = {"url": schema_registry_url}
        self.schema_registry_client = SchemaRegistryClient(schema_registry_conf)
        print(f"connect success on port: {kafka_broker}")

        self.protobuf_serializer = ProtobufSerializer(
            news_message_pb2.NewsMessage,
            self.schema_registry_client,
            conf={"use.deprecated.format": True},
        )
        self.string_serializer = StringSerializer("utf8")

    def json_serializer(data):
        return json.dumps(data).encode("utf-8")

    def delivery_report(err, msg):
        if err is not None:
            print(f"Delivery failed for message {msg.key()}: {err}")
            return
        print(
            f"Message {msg.key()} successfully produced to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
        )

    def send_news_to_kafka(self, json_data):
        print("start")
        self.kafka_producer.poll(0.0)

        news_message = news_message_pb2.NewsMessage(
            data=json_data["data"],
            category=json_data["category"],
            date=json_data["date"],
            publisher=json_data["publisher"],
            url=json_data["url"],
        )
        print(news_message)
        topic = "scraped-news"

        try:
            self.kafka_producer.produce(
                topic=topic,
                key=self.string_serializer(json_data["category"]),
                value=self.protobuf_serializer(
                    news_message, SerializationContext(topic, MessageField.VALUE)
                ),
                on_delivery=self.delivery_report,
            )
            print("already send")
        except KafkaError as e:
            print(f"Failed to send message to Kafka: {e}")

        finally:
            # Ensure all messages are flushed
            self.kafka_producer.flush()

    def GetNews(self, request, context):
        query = {}
        if request.category:
            query["category"] = request.category
        if request.date:
            query["date"] = request.date

        news_items = self.collection.find(query)
        response = news_service_pb2.GetNewsResponse()
        for item in news_items:
            news_item = response.news.add()
            news_item.data = item["data"]
            news_item.category = item["category"]
            news_item.date = item["date"]
            news_item.publisher = item["publisher"]
            news_item.url = item["url"]
        return response

    def GetOneNews(self, request, context):
        try:
            news_item = self.collection.find_one({"_id": ObjectId(request.id)})
            if not news_item:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("News item not found")
                return news_service_pb2.GetNewsResponse()

            response = news_service_pb2.GetNewsResponse()
            news = response.news.add()
            news.data = news_item["data"]
            news.category = news_item["category"]
            news.date = news_item["date"]
            news.publisher = news_item["publisher"]
            news.url = news_item["url"]

            return response

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error: " + str(e))
            return news_service_pb2.GetNewsResponse()

    def UpdateNews(self, request, context):
        # Create a query to find the news item by ID
        query = {"_id": ObjectId(request.id)}

        # Create an update dictionary based on the request fields
        update = {}
        if request.data:
            update["data"] = request.data
        if request.category:
            update["category"] = request.category
        if request.publisher:
            update["publisher"] = request.publisher
        if request.date:
            update["date"] = request.date
        if request.url:
            update["url"] = request.url

        # Perform the update operation in MongoDB
        result = self.collection.update_one(query, {"$set": update})

        # Create a response
        response = news_service_pb2.UpdateNewsResponse()
        if result.matched_count == 1:
            response.success = True
            response.message = "News item updated successfully"
        else:
            response.success = False
            response.message = "News item not found"

        return response

    def DeleteNews(self, request, context):
        # Create a query to find the news item by ID
        query = {"_id": ObjectId(request.id)}

        # Perform the delete operation in MongoDB
        result = self.collection.delete_one(query)

        # Create a response
        response = news_service_pb2.DeleteNewsResponse()
        if result.deleted_count == 1:
            response.success = True
            response.message = "News item deleted successfully"
        else:
            response.success = False
            response.message = "News item not found"

        return response

    def ScrapeNews(self, request, context):
        try:
            self.CreateNewsElement(request.url)
            print(request)
            return news_service_pb2.ScrapeNewsResponse(success=True)
        except Exception as e:
            print(f"Error scraping news: {str(e)}")
            return news_service_pb2.ScrapeNewsResponse(success=False)

    def CreateNewsElement(self, url, date=""):
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = bs(res.text, "html.parser")

        # Extract all URLs from the sitemap
        allURLsSoup = soup.select("url")

        def CallElement(url, date=""):
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
                # Prepare the JSON data
                # url = urllib.parse.quote(url, safe=':/')
                json_data = {
                    "data": data,
                    "category": category,
                    "date": date,
                    "publisher": "Dailynews",
                    "url": url,
                }
                print(f"available date {date}")
                # Store in MongoDB
                self.collection.insert_one(json_data)

                # Send to Kafka
                # self.kafka_producer.send(
                #     "news_topic", json.dumps(json_data).encode("utf-8")
                # )
                print(f"sending news to kafka...")
                # json_string = json.dumps(json_data).encode("utf-8")
                self.send_news_to_kafka(json_data)

            except Exception as e:
                print(f"Error processing URL {url}: {e}")

        # Loop through all URLs found in the sitemap
        n = 0
        for e in allURLsSoup:
            try:
                loc = e.find("loc").text
                lastmod = e.find("lastmod").text if e.find("lastmod") else ""
                CallElement(loc, lastmod)
                n += 1
            except Exception as e:
                print(f"Error with sitemap element: {e}")
                continue
            if n == 2:
                break


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    news_service_pb2_grpc.add_NewsServiceServicer_to_server(NewsService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("server start connection on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
