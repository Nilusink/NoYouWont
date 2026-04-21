import geopandas as gpd
import math as m
import os

os.environ["OGR_INTERLEAVED_READING"] = "YES"


lat, lon = 46.9550515,11.0113153
radius = 500  # 5 km


def bounding_box(lat_center, lon_center, radius_m):
    """
    Returns a bounding box around (lat_center, lon_center) with a radius in meters.
    Format: (lat_min, lon_min, lat_max, lon_max)
    This ensures the box fully contains the circle of the given radius.
    """
    # Approx meters per degree latitude
    meters_per_deg_lat = 111132.92 - 559.82 * m.cos(
        2 * m.radians(lat_center)) + \
                         1.175 * m.cos(4 * m.radians(lat_center))

    # Approx meters per degree longitude
    meters_per_deg_lon = 111412.84 * m.cos(m.radians(lat_center)) - \
                         93.5 * m.cos(3 * m.radians(lat_center))

    delta_lat = radius_m / meters_per_deg_lat
    delta_lon = radius_m / meters_per_deg_lon

    lat_min = lat_center - delta_lat
    lat_max = lat_center + delta_lat
    lon_min = lon_center - delta_lon
    lon_max = lon_center + delta_lon

    return lon_min, lat_min, lon_max, lat_max


roads = gpd.read_file(
    "roads.gpkg",
    layer="lines",
    engine="pyogrio",
    bbox=bounding_box(lat, lon, radius)
)
# roads.to_parquet("roads.parquet")
# exit(0)
print("loaded roads")
print(roads.columns)
print(len(roads))
print(roads.head())

street_types = [
    "motorway", "trunk", "primary", "secondary",
    "tertiary", "residential", "unclassified",
    "service", "living_street"
]

# fill other tags
roads["access"] = roads["other_tags"].str.extract(r'access=([^,|"]+)', expand=False)
roads["access"] = roads["access"].fillna("unknown")
roads["motor_vehicle"] = roads["other_tags"].str.extract(r'motor_vehicle=([^,|"]+)', expand=False)
roads["motor_vehicle"] = roads["motor_vehicle"].fillna("unknown")
roads["maxspeed"] = roads["other_tags"].str.extract(
    r'maxspeed:type"=>"([^"]+)"',
    expand=False
)
roads["maxspeed"] = roads["maxspeed"].fillna("unknown")

# filter road types
road_nodes = roads[
    roads["highway"].isin(street_types)
    & (roads["access"].isna() | ~roads["access"].isin(["private", "no"]))
    & (roads["motor_vehicle"].isna() | (roads["motor_vehicle"] != "no"))
]

print(len(road_nodes), type(road_nodes))
print(road_nodes.iloc[1])
geo = road_nodes.iloc[1]["geometry"]
# print(geo.iloc[0])
