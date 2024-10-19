import grpc
import requests
from bs4 import BeautifulSoup as bs
import os
from concurrent import futures
import json
from confluent_kafka import Producer
from pymongo import MongoClient
from traitlets import This
from proto import news_service_pb2
from proto import news_service_pb2_grpc
from scrape import dailynews_scrape, pptv_scrape, thairath_scrape, get_current_url
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
        self.mongo_client = MongoClient(
            "mongodb://localhost:27017/"
        )  # mongodb://mongodb:27017/
        self.db = self.mongo_client["news_db"]
        self.collection = self.db["news"]
        self.kafka_producer = Producer({"bootstrap.servers": "localhost:9092"})
        schema_registry_url = os.environ.get(
            "SCHEMA_REGISTRY_URL", "http://localhost:8081"
        )
        schema_registry_conf = {"url": schema_registry_url}
        self.schema_registry_client = SchemaRegistryClient(schema_registry_conf)
        self.protobuf_serializer = ProtobufSerializer(
            news_message_pb2.NewsMessage,
            self.schema_registry_client,
            conf={"use.deprecated.format": True},
        )
        self.string_serializer = StringSerializer("utf8")

    def delivery_report(err, msg, extra_info=None):
        if err is not None:
            print("Message delivery failed: {}".format(err))
        else:
            print("Message delivered to {} [{}]".format(msg.topic(), msg.partition()))

        if extra_info is not None:
            print("Additional info: {}".format(extra_info))

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

    def ScrapeNews(self, request, context):
        try:
            self.CreateNewsElement()
            print(request)
            return news_service_pb2.ScrapeNewsResponse(success=True)
        except Exception as e:
            print(f"Error scraping news: {str(e)}")
            return news_service_pb2.ScrapeNewsResponse(success=False)

    def CreateNewsElement(self):
        dailynews_url = get_current_url.getCurrentDailynews()
        thairath_url = get_current_url.getCurrentThairath()
        pptv_url = get_current_url.getCurrentPPTV()
        count = 3

        self.kafka_producer.poll(0.0)
        dailynews_scrape.ScrapeNews(count, dailynews_url, self)
        thairath_scrape.ScrapeNews(count, thairath_url, self)
        pptv_scrape.ScrapeNews(count, pptv_url, self)
        self.kafka_producer.flush()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    news_service_pb2_grpc.add_NewsServiceServicer_to_server(NewsService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
