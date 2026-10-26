"""
road_data_converter.py
26.10.2026

convert open-streetmap data to road geopackage

Author:
Nilusink
"""
from pyrosm import OSM

osm = OSM("europe-latest.osm.pbf")

roads = osm.get_network(
    network_type="driving",
    extra_attributes=[
        "access",
        "motor_vehicle",
        "maxspeed",
        "maxspeed:type"
    ]
)

print(roads.columns)