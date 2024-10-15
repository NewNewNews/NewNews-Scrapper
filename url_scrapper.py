import os
import json
from scrape import dailynews_scrape, pptv_scrape, thairath_scrape, get_current_url
import argparse


def load_urls_from_json(json_file):
    with open(json_file, "r") as file:
        urls = json.load(file)
    return urls


def scrape_news_from_urls(urls):
    if "dailynews" in urls:
        os.makedirs(os.path.dirname("data/dailynews_news_temp"), exist_ok=True)
        dailynews_scrape.ScrapeNews(-1, urls["dailynews"], "", "", True)

    if "pptv" in urls:
        os.makedirs(os.path.dirname("data/pptv_news_temp"), exist_ok=True)
        pptv_scrape.ScrapeNews(-1, urls["pptv"], "", "", True)

    if "thairath" in urls:
        os.makedirs(os.path.dirname("data/thairath_news_temp"), exist_ok=True)
        thairath_scrape.ScrapeNews(10, urls["thairath"], "", "", True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape news from URLs provided in a JSON file."
    )
    parser.add_argument(
        "json_file_path", type=str, help="Path to the JSON file containing URLs"
    )
    args = parser.parse_args()

    json_file_path = args.json_file_path
    urls = load_urls_from_json(json_file_path)
    scrape_news_from_urls(urls)
