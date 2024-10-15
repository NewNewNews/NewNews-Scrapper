import requests
from bs4 import BeautifulSoup as bs


def extract_news_data(url, headers=None, date=""):
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # Fetch the page content
        res = requests.get(url, headers=headers)
        soup = bs(res.text, "lxml")

        # Extract the category
        category = (
            soup.find("div", {"data-elementor-type": "single-post"})
            .find("nav", recursive=False)
            .find("div")
            .find("div")
        )
        category = category.find_all("a")[-1].text

        # category = map_category(category)  # Assuming the map_category function exists

        # Extract the content
        content = soup.find("main")
        if content is None:
            return None

        data = content.select("p")
        data = " ".join(p.get_text(strip=True) for p in data)
        data = data.replace(",", " ")  # Replace commas to avoid breaking CSVs if needed

        # Prepare the JSON data
        json_data = {
            "data": data,
            "category": category,
            "date": date,
            "publisher": "Dailynews",
            "url": url,
        }

        return json_data

    except Exception as e:
        print(f"Error extracting data: {e}")
        return None


url = "https://www.dailynews.co.th/news/3782240/"
news_data = extract_news_data(url)
print(news_data["data"])
