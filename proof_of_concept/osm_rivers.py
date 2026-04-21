import requests, json

# Example: all rivers in a 5 km bounding box
lat, lon = 47.2692, 11.4041
radius = 20000  # 5 km

query = f"""
[out:json];
(
  way["waterway"~"river|canal"](around:{radius},{lat},{lon});
);
out geom;
"""

#   relation["waterway"~"river|canal"](around:{radius},{lat},{lon});

url = "https://overpass-api.de/api/interpreter"
response = requests.get(url, params={"data": query})
response.raise_for_status()
print(response.status_code, response.headers.get("Content-Type"))
data = response.json()

with open("buffer_rivers.json", "w") as f:
    json.dump(data, f, indent=4)


# rivers = []
# for way in data.ways:
#     points = [(float(node.lat), float(node.lon)) for node in way.nodes]
#     rivers.append(points)
#
# print(f"Found {len(rivers)} rivers/streams/canals")
