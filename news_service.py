import grpc
import requests
from bs4 import BeautifulSoup as bs
from concurrent import futures
import json
from kafka import KafkaProducer
from pymongo import MongoClient
from proto import news_service_pb2
from proto import news_service_pb2_grpc


class NewsService(news_service_pb2_grpc.NewsServiceServicer):
    def __init__(self):
        self.mongo_client = MongoClient(
            "mongodb://localhost:27017/"
        )  # mongodb://mongodb:27017/
        self.db = self.mongo_client["news_db"]
        self.collection = self.db["news"]
        self.kafka_producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"]
        )  # "localhost:9092"   "kafka:9092"

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
                self.collection.insert_one(json_data)

                # Send to Kafka
                self.kafka_producer.send(
                    "news_topic", json.dumps(json_data).encode("utf-8")
                )

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
            if n == 10:
                break


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    news_service_pb2_grpc.add_NewsServiceServicer_to_server(NewsService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
