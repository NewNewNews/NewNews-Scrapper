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

import datetime
import torch
from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from pymilvus.model import DefaultEmbeddingFunction
from sklearn.cluster import DBSCAN


class NewsService(news_service_pb2_grpc.NewsServiceServicer):
    def __init__(self):
        self.mongo_client = MongoClient(
            os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
        )
        self.db = self.mongo_client["news_db"]
        self.collection = self.db["news"]
        self.kafka_producer = Producer({"bootstrap.servers": os.environ.get("KAFKA_BROKER", "localhost:9092")})
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
        
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        
        """
        self.embedding_function = BGEM3EmbeddingFunction(
            model_name='BAAI/bge-m3', # Specify the model name
            device=device, # Specify the device to use, e.g., 'cpu' or 'cuda:0'
            use_fp16=False # Specify whether to use fp16. Set to `False` if `device` is `cpu`.
        )
        """
        
        self.embedding_function = DefaultEmbeddingFunction()
        
        self.clustering = DBSCAN()

    def cluster(self):
        print("START CLUSTERING...")
        
        # [x] update new key `datatime`: convert raw date to datetime in mongo
        news_items = self.collection.find()
        
        for item in news_items:
            date = item["date"]
            # date = datetime.datetime(date)
            date = date.split("T")[0]
            date = datetime.datetime.strptime(date, "%Y-%m-%d")
            self.collection.update_one({"_id": item["_id"]}, {"$set": {"datetime": date}})
        
        # [x] query today news
        today = datetime.datetime.today()
        
        # exclude time 
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + datetime.timedelta(days=1)
        print(type(today), today)

        news_items = self.collection.find({
            "datetime":{
                "$gte": today,
                "$lt": tomorrow
            }
        })
        
        news_docs = []
        news_data = []
        for item in news_items:
            news_docs.append(item)
            news_data.append(item["data"][:512]) # make sure data context length is less than model context length
        
        print("len(news_data):", len(news_data))
        
        print("news_chars:", [len(news) for news in news_data])
        
        # [x] compute embeddings
        embeddings = self.embedding_function.encode_documents(news_data)
        # print("embeddings:", embeddings[0].shape, len(embeddings))
        
        # [x] compute dbscan
        self.clustering.fit(embeddings)
        # print(self.clustering.labels_) # [-1, -1, 0, 0, 1, 1, 1]
        
        # create pair of news and cluster labels
        # sort docs by cluster labels
        news_docs = sorted(zip(news_docs, self.clustering.labels_), key=lambda x: x[1])
        # print("news_docs:", [label for _, label in news_docs])
        
        # sort labels
        self.clustering.labels_ = sorted(self.clustering.labels_)
        # print(self.clustering.labels_) # [-1, -1, 0, 0, 1, 1, 1]
        
        # sort news_docs by cluster labels
        news_docs = [doc for doc, _ in news_docs]
        
        # [ ] update news with event id
        for i, item in enumerate(news_docs):
            # print(item["_id"], self.clustering.labels_[i])
            item["event_id"] = self.clustering.labels_[i]
            self.collection.update_one({"_id": item["_id"]}, {"$set": {"event_id": int(self.clustering.labels_[i])}})
            
            news_message = news_message_pb2.NewsMessage(
                data=item["data"],
                category=item["category"],
                date=item["date"],
                publisher=item["publisher"],
                url=item["url"],
            )
            
            topic = "news_event_topic"
            key = f"{item['event_id']:04d}_{item['date']}"
            try:
                self.kafka_producer.produce(
                    topic=topic,
                    key=self.string_serializer(key),
                    value=self.protobuf_serializer(
                        news_message, SerializationContext(topic, MessageField.VALUE)
                    ),
                    on_delivery=self.delivery_report,
                )
                print(f"Message sent to Kafka: {key}")
            except Exception as e:
                print(f"Failed to send message to Kafka: {e}")
                
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
            return news_service_pb2.ScrapeNewsResponse(success=True)
        except Exception as e:
            print(f"Error scraping news: {str(e)}")
            return news_service_pb2.ScrapeNewsResponse(success=False)
        
    def CreateNewsElement(self):
        # dailynews_url = get_current_url.getCurrentDailynews()
        # thairath_url = get_current_url.getCurrentThairath()
        # pptv_url = get_current_url.getCurrentPPTV()
        
        # count = 3

        # self.kafka_producer.poll(0.0)
        # dailynews_scrape.ScrapeNews(count, dailynews_url, self)
        # thairath_scrape.ScrapeNews(count, thairath_url, self)
        # pptv_scrape.ScrapeNews(count, pptv_url, self)
        # self.kafka_producer.flush()
        
        self.cluster()

    def UpdateNews(self, request, context):
        url = request.url
        update_data = {}

        if request.data != "":
            update_data["data"] = request.data
        if request.category != "":
            update_data["category"] = request.category
        if request.date != "":
            update_data["date"] = request.date
       
        result = self.collection.update_one(
            {"url": url},
            {"$set": update_data}
        )
       
        if result.modified_count == 0:
            return news_service_pb2.UpdateNewsResponse(success=False, message = "Can't find news with URL")
        return news_service_pb2.UpdateNewsResponse(success=True, message = "Update complete")

    def DeleteNews(self, request, context):
        try:
            if request.url:
                filter_criteria = {"url": request.url}
            else:
                return news_service_pb2.DeleteNewsResponse(success=False, message = "Missing URL")

            result = self.collection.delete_one(filter_criteria)

            if result.deleted_count == 0:
                return news_service_pb2.DeleteNewsResponse(success=False, message = "Can't find news with URL")

            return news_service_pb2.DeleteNewsResponse(success=True, message = "Delete complete")

        except Exception as e:
            return news_service_pb2.UpdateNewsResponse(success=False, message = "Error with delete news")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    news_service_pb2_grpc.add_NewsServiceServicer_to_server(NewsService(), server)
    port = os.getenv("PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Server started on port {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
