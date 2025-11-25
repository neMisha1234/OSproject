import requests
from datetime import datetime
def get_info_event():
    url = 'https://kudago.com/public-api/v1.2/events/?page_size=1&expand=place&location=msk&dates,participants&fields=dates,id,title,description,place,location'
    event = requests.get(url).json()
    txt = 'Событие:'+event['results'][0]['title']+'\n'+'Описание:'+event['results'][0]['description'].strip('<p>').replace('</p>','')+'Дата:'+ str(datetime.fromtimestamp(event['results'][0]['dates'][0]['start']).strftime('%Y-%m-%d'))
    return txt
print(get_info_event())
