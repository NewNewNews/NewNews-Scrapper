import grpc
from proto import news_service_pb2
from proto import news_service_pb2_grpc


def run():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = news_service_pb2_grpc.NewsServiceStub(channel)
        response = stub.ScrapeNews(news_service_pb2.ScrapeNewsRequest())
        if response.success:
            print("News scraping initiated successfully.")
        else:
            print("Failed to initiate news scraping.")


if __name__ == "__main__":
    run()
