import os
import requests
import json
from datetime import datetime

from bs4 import BeautifulSoup as bs

central_categories = {
        'Sports': [
            'บุนเดสลีกา', 'ลาลีกา', 'พรีเมียร์ลีก', 'กีฬาไทย', 
            'มวยสากล', 'ทีมชาติไทย', 'ฟุตบอลทั่วไป', 'มวยไทย'
        ],
        'Entertainment': [
            'บันเทิง', 'Daily Beauty', 'นวัตกรรมขนส่ง'
        ],
        'Politics & Society': [
            'การเมือง', 'ประชาสัมพันธ์', 'สังคม', 'ต่างประเทศ'
        ],
        'Lifestyle & Culture': [
            'ท่องเที่ยว-ที่พัก', 'การศึกษา-ศาสนา', 'เศรษฐกิจ'
        ],
        'News & Current Affairs': [
            'เทคโนโลยี', 'อาชญากรรม', 'กทม.', 'ทั่วไทย', 'เกษตร'
        ]
    }

def ScrapeNews(n, url, newServices, date="", dev_mode = False):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = bs(res.text, "html.parser")

    allURLsSoup = soup.select("url")

    count = 0
    for e in allURLsSoup:
        try:
            loc = e.find("loc").text
            lastmod = e.find("lastmod").text if e.find("lastmod") else ""
            if lastmod != "":
                lastmod = datetime.fromisoformat(lastmod)
                lastmod = lastmod.strftime("%Y-%m-%dT%H:%M:%S")

            print('lastmod:', lastmod)
            CallElement(loc, headers, newServices, dev_mode, lastmod)
            count += 1
        except Exception as e:
            print(f"Error with sitemap element: {e}")
            continue
        if count == n:
            break

def CallElement(url, headers, newServices, dev_mode, date=""):
    try:
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
        category = map_category(category)

        # Extract the content
        content = soup.find("main")
        if content is None:
            return

        data = content.select("p")
        data = " ".join(p.get_text(strip=True) for p in data)
        data = data.replace(",", " ")

        # Prepare the JSON data
        json_data = {
            "data": data,
            "category": category,
            "date": date,
            "publisher": "Dailynews",
            "url": url,
        }

        # Store in MongoDB
        if (not dev_mode):            
            newServices.collection.insert_one(json_data)

            json_data.pop('_id')
            
            import uuid
            import numpy as np
            
            vector_data = json_data.copy()
            print(vector_data.keys())
            
            vector_data['news_id'] = np.int64(uuid.uuid1().int>>65) # think about this !!!
            # vector_data['news_id'] = np.int64(int(uuid.uuid4().int & (1<<64)-1))
            
            # t = uuid.uuid1().int>>64
            # print(t)
            # print(int(t))
            vector_data['id'] = vector_data.pop('news_id')
            # vector_data['id'] = 1
            
            print(vector_data.keys())
            
            # Send to Milvus
            print("sending to Milvus starting")
            vector_data["vector"] = newServices.embedding_func.encode_documents([vector_data["data"]])['dense'][0]
        
            print(vector_data.keys())
            
            print("sending to Milvus collection")
            if not newServices.vector_db.has_collection(newServices.vector_collection):
                # newServices.vector_db.drop_collection(collection_name=newServices.vector_collection)
                newServices.vector_db.create_collection(
                    collection_name=newServices.vector_collection,
                    dimension=1024,
                )
                
            # if newServices.vector_db.has_collection(newServices.vector_collection):
            #     newServices.vector_db.drop_collection(collection_name=newServices.vector_collection)
            #     newServices.vector_db.create_collection(
            #         collection_name=newServices.vector_collection,
            #         dimension=1024,
            #     )
            print("sending to Milvus inserting")
            
            print(vector_data.keys())

            [print(k, type(x)) for k, x in vector_data.items()]
            print(vector_data['id'])
            import sys
            print(sys.getsizeof(int))
            print(sys.getsizeof(vector_data['id']))
            
            print('searching in Milvus')
            search_res = newServices.vector_db.search(
                collection_name=newServices.vector_collection,
                data=[vector_data["vector"]],
                limit=3
            )
            
            import pprint
            pprint.pprint(search_res)
            
            res = newServices.vector_db.insert(
                collection_name=newServices.vector_collection,
                data=[vector_data]
            )
            print("sending to Milvus finished")
            print(res)            
            
            print('searching in Milvus')
            search_res = newServices.vector_db.search(
                collection_name=newServices.vector_collection,
                data=[vector_data["vector"]],
                limit=3
            )
            
            import pprint
            pprint.pprint(search_res)
            
            # Send to Kafka
            newServices.kafka_producer.send(
                "news_topic", json.dumps(json_data).encode("utf-8")
            )
            
        else:
            with open("../data_temp/dailynews_news_temp", 'a', encoding = "utf-8") as file:
                json.dump(json_data, file, ensure_ascii = False, indent = 5)

    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        exit()

def map_category(news_category):
    for central, categories in central_categories.items():
        if news_category in categories:
            return central
    return 'Etc'