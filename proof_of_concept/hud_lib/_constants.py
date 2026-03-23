"""
_constants.py
22.03.2026

shared constant values

Author:
Nilusink
"""
SCREEN_RADIUS = 120

MAX_ROADS = 150_000
MAX_CAMS = 2000

REQUEST_RADIUS = 20_000
ROADS_REQUEST_RADIUS = 15_000  # if 15km from last request, = 5km before running out
REQUEST_TIMEOUT = 60

CAMS_UPDATE_FREQ = 60
GPS_UPDATE_FREQ = 1

ROAD_TYPES: dict[str, int] = {
    # Major roads
    "motorway": 0,
    "motorway_link": 0,

    "trunk": 1,
    "trunk_link": 1,

    "primary": 2,
    "primary_link": 2,

    "secondary": 3,
    "secondary_link": 3,

    "tertiary": 4,
    "tertiary_link": 4,

    # Normal roads
    "unclassified": 5,
    "residential": 6,
    "living_street": 7,
    "service": 8,

    # Special drivable / edge
    "road": 9,          # unknown classification
    "escape": 10,
    "bus_guideway": 11,

    # Rural / low importance
    "track": 12,
    "rest_area": 13,

    # Non-car infrastructure
    "pedestrian": 100,
    "footway": 101,
    "cycleway": 102,
    "path": 103,
    "bridleway": 104,
    "steps": 105,

    # Rare / special
    "corridor": 110,    # indoor mapped ways
    "platform": 111,    # public transport platforms

    # Lifecycle states
    "construction": 200,
    "proposed": 201,
    "abandoned": 202,
    "disused": 203,
    "ladder": 204,
    "scramble": 205,

    # Other uncommon
    "raceway": 210,
    "busway": 211,      # bus-only roads (newer tag)
}

SPEED_TYPES: dict[str, int] = {
    # Austria default zones
    "AT:urban": 50,
    "AT:rural": 100,
    "AT:trunk": 100,
    "AT:highway": 130,
    "AT:residential": 30,
    "AT:school": 30,
    "AT:construction": 60,
    "AT:variable": 0,  # must read sign
    "AT:none": 130,    # motorway with no explicit limit

    # Germany examples (common)
    "DE:urban": 50,
    "DE:rural": 100,
    "DE:zone30": 30,
    "DE:autobahn": 130,

    # Switzerland examples
    "CH:urban": 50,
    "CH:rural": 80,
    "CH:autobahn": 120,

    # Other generic codes
    "walk": 5,
    "signals": 0,     # obey traffic lights
    "none": 130,      # no limit → default high-speed
    "national": 100,
    "living_street": 20,
}
