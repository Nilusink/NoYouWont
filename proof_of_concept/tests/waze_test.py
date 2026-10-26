import requests
import json

URL = (
    "https://www.waze.com/row-rtserver/web/TGeoRSS?"
    "bottom=47.2&"
    "top=47.3&"
    "left=11.3&"
    "right=11.5&"
    "ma=200&"
    "types=alerts"
)


response = requests.get(URL)
print(response.text)
# print(json.dumps(data, indent=4))
