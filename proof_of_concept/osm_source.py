import requests
import json

# Center coordinate
lat, lon = 47.2692, 11.4041
radius = 20000  # 5 km

# Overpass QL query: all highways except footways, cycleways, paths, tracks
overpass_query = f"""
[out:json];
(
  way["highway"]["highway"!~"footway|cycleway|path|track|steps|elevator|service"](around:{radius},{lat},{lon});
);
out geom;
"""

url = "https://overpass-api.de/api/interpreter"
# url = "https://lz4.overpass-api.de/api/interpreter"
response = requests.get(url, params={"data": overpass_query})
response.raise_for_status()
data = response.json()

with open("buffer.json", "w") as f:
    json.dump(data, f, indent=4)

# data = json.load(open("buffer.json", "r"))

# Print info
for element in data.get("elements", []):
    highway_type = element.get("tags", {}).get("highway")
    name = element.get("tags", {}).get("name", "unknown")
    print(f"Way ID {element['id']}: {highway_type}, {name}")


print(json.dumps(data["elements"][0], indent=4))
