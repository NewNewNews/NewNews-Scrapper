import requests
from bs4 import BeautifulSoup as bs
import re


def extract_news_data(url, headers=None):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # Extract the category from the URL
        category = url.split("/")[3:]
        if category[0] == "news":
            category = category[1]
        else:
            category = category[0]
        # category = map_category(category)  # Assuming the map_category function exists

        # Fetch the page content
        res = requests.get(url, headers=headers)
        soup = bs(res.text, "html.parser")

        # Extract the date
        date = soup.find("div", class_=re.compile(r"__item_article-date.*\bcss\b"))
        if date is None:
            date = getDate()  # Assuming getDate() provides a default date
        else:
            date = date.getText()

        # Extract the content
        content = soup.find("div", {"itemprop": "article-body"}) or soup.find(
            "div", {"itemprop": "articleBody"}
        )
        if content is None:
            return None

        data = content.select("p")
        data = " ".join(p.get_text(strip=True) for p in data)
        data = data.replace(",", " ")  # Replacing commas to avoid CSV issues

        # Prepare the JSON data
        json_data = {
            "data": data,
            "category": category,
            "date": date,
            "publisher": "Thairath",
            "url": url,
        }

        return json_data

    except Exception as e:
        print(f"Error extracting data from Thairath: {e}")
        return None


url = "https://www.thairath.co.th/news/politic/2809879"
news_data = extract_news_data(url)
print(news_data["data"])
print(news_data.keys())
