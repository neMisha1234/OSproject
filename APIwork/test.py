import requests

response = requests.get("https://kudago.com/public-api/v1.4/event-categories/")
print(response.json())