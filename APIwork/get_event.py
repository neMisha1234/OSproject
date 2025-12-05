import random
import requests
from datetime import datetime
import textwrap
import time
from PIL import Image
from urllib.request import urlopen


def wrap_by_words(text, width=50):
    return "\n".join(textwrap.wrap(text, width=width))


def get_info_event():
    # url = 'https://kudago.com/public-api/v1.2/events/?page_size=1&expand=place%2Clocation%2Cdates&location=msk&dates,participants&fields=dates,id,title,description,place,location&actual_since=int(time.time())'
    actual_since = int(time.time())
    # url = (
    #    "https://kudago.com/public-api/v1.2/events/"
    #   "?page_size=1"
    #    "&location=msk"
    #    "&expand=place,dates,location"
    #    "&fields=dates,id,title,description,place,location,site_url"
    #    f"&actual_since={actual_since}"
    # )
    url = f'https://kudago.com/public-api/v1.4/search/?q=концерт&page={random.randint(1,100)}&page_size=1&expand=dates,url,place&ctype=event&location=msk'
    event = requests.get(url).json()
    date = datetime.fromtimestamp(event['results'][0]['daterange']['start']).strftime('%Y-%m-%d')
    description = event['results'][0]['body_text']
    start = description.find('"text":"') + len('"text":"')
    end = description.find('"', start)
    description = wrap_by_words(description[start:end], 50)
    # wrap_by_words(event['results'][0]['body_text'].replace('<p>','').replace('</p>',''), 50)
    title = event['results'][0]['title']
    place = event['results'][0]['place']['title']
    image_url = event['results'][0]['first_image']['image']
    # txt = 'Событие:'+title+'\n'+'Описание:'+wrap_by_words(description.strip('<p>').replace('</p>',''), 50)+'\n'+'Дата:'+ str(datetime.fromtimestamp(date).strftime('%Y-%m-%d'))
    text = (f"Событие: {title}\n"
            f"Описание: {description}\n"
            f"Дата: {date}\n"
            f"Место: {place}")
    return image_url, text

# datetime.fromtimestamp(date).strftime('%Y-%m-%d')
