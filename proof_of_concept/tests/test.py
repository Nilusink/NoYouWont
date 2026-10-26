from time import sleep
import math as m
import requests
import json
import re


lat, lon = 47.2534446,11.3498165
radius = 20000  # 5 km


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

    return lat_min, lon_min, lat_max, lon_max


MOBILE_TYPE = "0,1,2,3,4,5,6"
FIXED_TYPE = "101,102,103,104,105,106,107,108,109,110,111,112,113,114,115"

get_type = MOBILE_TYPE + "," + FIXED_TYPE
# bbox = ",".join([str(v) for v in bounding_box(lat, lon, radius)])
bbox = "47.2200,10.8200,46.8500,11.0800"


# URL = f"https://cdn2.atudo.net/api/1.0/vl.php?type={get_type}&box=47.24221577256205,11.364455837603446,47.29618422743795,11.443744162396554"
URL = (
   'https://cdn2.atudo.net/api/1.0/vl.php'
   '?clusters=0'
   '&type=0,1,2,3,4,5,6,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115'
   '&box='
)


R = 5000
i = 1
while True:
    data = requests.get(URL + ",".join([str(v) for v in bounding_box(lat, lon, R*i)]))
    data = data.json()
    i += 1

    rtypes = []

    with open("cam_data.json", "w") as f:
        json.dump(data, f, indent=4)

    cluster = 0
    n_cluster_cams = 0
    for point in data["pois"]:
        # if point["type"] != '1':
        #     print(json.dumps(point, indent=4))

        if point["type"] not in rtypes:
            rtypes.append(point["type"])

        if "count_cluster" in point["info"]:
            cluster += 1
            n_cluster_cams += int(re.findall("\d+", point["info"])[0])

    print(rtypes)

    print(len(data["pois"]))
    print(cluster, n_cluster_cams)

    sleep(2)
