import grpc
import requests
from bs4 import BeautifulSoup as bs

from concurrent import futures
import json
from kafka import KafkaProducer
from pymongo import MongoClient
from pymilvus import MilvusClient
from pymilvus.model.hybrid import BGEM3EmbeddingFunction
from proto import news_service_pb2
from proto import news_service_pb2_grpc
from scrape import dailynews_scrape, pptv_scrape, thairath_scrape, get_current_url

class NewsService(news_service_pb2_grpc.NewsServiceServicer):
    def __init__(self):
        self.mongo_client = MongoClient(
            "mongodb://localhost:27017/"
        )  # mongodb://mongodb:27017/
        self.db = self.mongo_client["news_db"]
        self.collection = self.db["news"]
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            api_version=(2, 0, 2)
        )  # "localhost:9092"   "kafka:9092"
        
        self.vector_db = MilvusClient("http://localhost:19530")
        # self.vector_db = MilvusClient("milvus/milvus_demo.db")
        
        self.vector_collection = "news_collection"
        
        self.embedding_func = BGEM3EmbeddingFunction(
            model_name='BAAI/bge-m3', # Specify the model name
            device='cpu', # Specify the device to use, e.g., 'cpu' or 'cuda:0'
            use_fp16=False # Specify whether to use fp16. Set to `False` if `device` is `cpu`.
        )

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

        dailynews_scrape.ScrapeNews(3, dailynews_url, self)
        # thairath_scrape.ScrapeNews(3, thairath_url, self)
        # pptv_scrape.ScrapeNews(3, pptv_url, self)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    news_service_pb2_grpc.add_NewsServiceServicer_to_server(NewsService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
