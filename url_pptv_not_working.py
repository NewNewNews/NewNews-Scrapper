import requests
from bs4 import BeautifulSoup as bs
import urllib.parse
import re


def extract_news_data(url, headers=None):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # Extract and process the category from the URL
        category = url.replace("https://www.pptvhd36.com/", "").split("/")
        # if needsEncoding(
        #     category[-2]
        # ):  # Assuming needsEncoding checks if encoding is required
        #     category = urllib.parse.unquote(category[-2])
        # elif category[-2] == "news":
        #     category = category[-3]
        # else:
        #     category = category[0]
        # category = map_category(category)  # Assuming map_category function exists

        # Fetch the page content
        res = requests.get(url, headers=headers)
        soup = bs(res.text, "lxml")

        print(soup)

        # Extract the date
        date = soup.find("time")
        if date is None:
            date = getDate()  # Assuming getDate() provides a default date
        else:
            date = date.getText()

        # Extract the content
        content = soup.find(
            "div", {"class": re.compile("content-details__body|sport_detail__body")}
        )

        if content is None:
            return None

        data = content.select("p")[2:]  # Skipping first two paragraphs
        data = " ".join(p.get_text(strip=True) for p in data)
        data = data.replace(",", " ")  # Replacing commas for CSV compatibility

        # Prepare the JSON data
        json_data = {
            "data": data,
            "category": category,
            "date": date,
            "publisher": "PPTV",
            "url": url,
        }

        return json_data

    except Exception as e:
        print(f"Error extracting data from PPTV: {e}")
        return None


url = "https://www.pptvhd36.com/wealth/economic/231071"
news_data = extract_news_data(url)
print(news_data)
