from time import sleep
import math as m
import requests
import json


lat, lon = 47.2534446,11.3498165


def bounding_box(lat_center: float, lon_center: float, radius_m: float):
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


TYPE_MOBILE = [0,1,2,3,4,5,6]
TYPE_TRAILER = ['ts']
TYPE_FIXED = [101,102,103,104,105,106,107,108,109,110,111,112,113,115,117,114]

CONTROL_KINDS = {
    "speed": ["1", "7", "107"],
    "redlight": ["2", "11", "111"],
    "redlight_speed": ["110"],
    "section_control": ["12", "112", "113"],
    "tunnel": ["114"],
    "distance": ["6", "101"],
    "weight": ["3", "108"],
    "height": ["109"],
    "lane": ["104"],
    "entry": ["105"],
    "access": ["103"],
    "crosswalk": ["106"],
    "overtaking": ["115"],
    "police": ["4", "117"],
    "alcohol": ["5"],
    "dummy": ["102"],
    "unknown": ["0"],
}


CODE_LABELS = {
    0: {"de": "Unbekannt", "en": "Unknown"},
    1: {"de": "Geschwindigkeitsblitzer", "en": "Speedcamera"},
    2: {"de": "Ampelblitzer", "en": "Redlight control"},
    3: {"de": "Gewichtskontrolle", "en": "Weight control"},
    4: {"de": "Allg. Verkehrskontrolle", "en": "Spot check on traffic"},
    5: {"de": "Alkoholkontrolle", "en": "Alcohol control"},
    6: {"de": "Abstandskontrolle", "en": "Distance control"},
    7: {"de": "Geschwindigkeitsblitzer", "en": "Speedcamera"},
    11: {"de": "Ampelblitzer", "en": "Redlight control"},
    12: {"de": "Section Control", "en": "Section Control"},
    20: {"de": "Stauende", "en": "End of tailback"},
    21: {"de": "Unfall", "en": "Accident"},
    22: {"de": "Tagesbaustelle", "en": "Temporary roadwork"},
    23: {"de": "Hindernis", "en": "Obstacle"},
    24: {"de": "Rutschgefahr", "en": "Slipperiness"},
    25: {"de": "Sichtbehinderung", "en": "Obstructed view"},
    26: {"de": "Dauerbaustelle", "en": "Permanent roadworks"},
    29: {"de": "Defektes Fahrzeug", "en": "Broken down vehicle"},
    101: {"de": "Abstandskontrolle", "en": "Distance control"},
    102: {"de": "Attrappe", "en": "Dummy"},
    103: {"de": "Auffahrtskontrolle", "en": "Access control"},
    104: {"de": "Spurkontrolle", "en": "Lane control"},
    105: {"de": "Einfahrtskontrolle", "en": "Entrance control"},
    106: {"de": "Fußgängerüberweg", "en": "Pedestrian crosswalk"},
    107: {"de": "Geschwindigkeitsblitzer", "en": "Speedcamera"},
    108: {"de": "Gewichtskontrolle", "en": "Weight control"},
    109: {"de": "Höhenkontrolle", "en": "Height control"},
    110: {"de": "Ampel- & Geschwindigkeitsblitzer", "en": "Redlight & speed control"},
    111: {"de": "Ampelblitzer", "en": "Redlight control"},
    112: {"de": "Abschnittskontrolle", "en": "Section Control Start"},
    113: {"de": "Abschnittskontrolle Ende", "en": "Section Control End"},
    114: {"de": "Blitzer im Tunnel", "en": "Speedcam inside tunnel"},
    115: {"de": "Überholverbot", "en": "Overtaking ban"},
    117: {"de": "Stationäre Polizeikontrolle", "en": "Stationary Police Check"},
    "closure": {"de": "Sperrung", "en": "Road block"},
    "vwd": {"de": "Polizeimeldung", "en": "Police reports"},
}

types = ",".join(map(str, TYPE_MOBILE + TYPE_TRAILER + TYPE_FIXED))


def get_url(bbox):
    return (
        "https://www.blitzer.de/karte/api/markers"
        f"?type={types}"
        f"&box={bbox}"
        "&z=18"
    )


R = 5000
i = 1
while True:
    bbox = ",".join([str(v) for v in bounding_box(lat, lon, R*i)])
    data = requests.get(get_url(bbox))
    i += 1

    data = data.json()

    print(len(data["pois"]))

    # print(json.dumps(data, indent=4))

    for blitzer in data["pois"]:
        if blitzer["type"] in CODE_LABELS:
            print(f"{CODE_LABELS[blitzer['type']]["en"]}: {blitzer['vmax']} km/h, {blitzer["info"]["kind"]}, {blitzer["address"]}")

        else:
            print(f"{blitzer["type"]}: {blitzer["counter"]}")

    sleep(2)