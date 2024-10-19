import grpc
from proto import news_service_pb2
from proto import news_service_pb2_grpc


def run():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = news_service_pb2_grpc.NewsServiceStub(channel)
        print("Connected to server.")

        while True:
            op = input("Enter operation (1: GetNews, 2: GetTodayNews, 3: ScrapeNews, q: Quit): ")
            if op == "1":
                category = "Etc"
                date = "2024-10-16T13:20:27+00:00"
                response = stub.GetNews(news_service_pb2.GetNewsRequest(
                    category=category,
                    date=date
                ))
                print(f'retrieved {len(response.news)} news:')
                for i, news in enumerate(response.news):
                    print(f'{i+1}: {news.url}')
            if op == "2":
                response = stub.GetTodayNews()
                if response.success:
                    print("Today's news retrieved successfully.")
                else:
                    print("Failed to retrieve today's news.")
            if op == "3":
                response = stub.ScrapeNews(news_service_pb2.ScrapeNewsRequest())
                if response.success:
                    print("News scraping initiated successfully.")
                else:
                    print("Failed to initiate news scraping.")
            if op == "q":
                print("Exit client.")
                break


if __name__ == "__main__":
    run()
