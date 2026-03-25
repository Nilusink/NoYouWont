"""
data_source.py
22.03.2026

Requests data from osm and atudo for use in the main process

Author:
Nilusink
"""
from multiprocessing import shared_memory, Event, Value
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter, sleep
from json import JSONDecodeError, loads, load
from dataclasses import dataclass
import numpy as np
import math as m
import requests

from hud_lib import road_t, speedcam_t, MAX_ROADS, MAX_CAMS, REQUEST_RADIUS, \
    REQUEST_TIMEOUT, CAMS_UPDATE_FREQ, ROADS_REQUEST_RADIUS, SPEED_TYPES, \
    ROAD_TYPES, position_point_t, GPS_UPDATE_FREQ, latlon_to_meters, \
    Vec2


# cam constants
MOBILE_TYPE = "0,1,2,3,4,5,6"
FIXED_TYPE = "101,102,103,104,105,106,107,108,109,110,111,112,113,114,115"


# road constants
OSM_BASE_URL = "https://overpass-api.de/api/interpreter"


@dataclass(frozen=True)
class RadarWarning:
    x: float
    y: float
    type: int
    vmax: int
    is_cluster: bool


@dataclass(frozen=True)
class StreetSegment:
    ax: float
    ay: float
    bx: float
    by: float
    priority: int
    vmax: int


def atudo_url(get_type: str, bbox: str) -> str:
    return f"https://cdn2.atudo.net/api/1.0/vl.php?type={get_type}&box={bbox}"


def overpass_query(radius: float, lat: float, lon: float) -> str:
    return f"""
[out:json];
(
  way["highway"]["highway"!~"footway|cycleway|path|track|steps|elevator|service"](around:{radius},{lat},{lon});
);
out geom;
"""


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


def heading_degrees(lat1, lon1, lat2, lon2):
    """
    Returns heading from point1 to point2 in degrees
    0 = north, 90 = east
    """
    lat1_r, lat2_r = m.radians(lat1), m.radians(lat2)
    dlon_r = m.radians(lon2 - lon1)

    x = m.sin(dlon_r) * m.cos(lat2_r)
    y = m.cos(lat1_r)*m.sin(lat2_r) - m.sin(lat1_r)*m.cos(lat2_r)*m.cos(dlon_r)
    heading = m.atan2(x, y)
    return (heading + 2*m.pi) % 2*m.pi  # normalize 0-2*m.pi


def start_data_source(
        set_cams_event: Event,
        set_roads_event: Event,
        quit_event: Event,
        roads_memory_name: str,
        cams_memory_name: str,
        n_roads: Value,
        n_cams: Value,
        curr_lat: Value,
        curr_lon: Value,
        curr_rot: Value,
        curr_speed: Value,
        comm
) -> None:
    """
    initialize data source and run continuously
    """
    d_start = perf_counter()

    comm.send("0")
    # make sure events are cleared
    set_roads_event.clear()
    set_cams_event.clear()

    roads_shm = shared_memory.SharedMemory(name=roads_memory_name)
    cams_shm = shared_memory.SharedMemory(name=cams_memory_name)

    cams_updating = False
    roads_updating = False

    last_cams_set = 0
    pos = (0, 0)  # gps position as coordinates
    last_update_pos = [0, 0]  # position as meters

    pool = ThreadPoolExecutor(max_workers=2)
    roads = (road_t * MAX_ROADS).from_buffer(roads_shm.buf)
    cams = (speedcam_t * MAX_CAMS).from_buffer(cams_shm.buf)

    pos_cache = (position_point_t * 3)()

    def end():
        del roads, cams
        comm.send("datasource end")
        quit_event.clear()

    def _update_cams() -> None:
        """
        update cams in background
        """
        nonlocal cams_updating, pos
        cams_updating = True

        # get data from atudo
        get_type = MOBILE_TYPE + "," + FIXED_TYPE
        bbox = ",".join(
            [str(v) for v in bounding_box(pos[0], pos[1], REQUEST_RADIUS)]
        )

        url = atudo_url(get_type, bbox)

        # try and get data until its working
        data = {}
        # while True:
        #     try:
        #         raw_data = requests.get(url, timeout=REQUEST_TIMEOUT)
        #
        #     except requests.exceptions.Timeout:
        #         # wait for 10 secs to not spam the api
        #         sleep(10)
        #         continue
        #
        #     try:
        #         data = raw_data.json()
        #
        #     except JSONDecodeError:
        #         # wait for 10 secs to not spam the api
        #         sleep(10)
        #         continue
        #
        #     break

        data = load(open("cam_data.json", "r"))

        # writing data, set lock
        radars = []
        # process cams
        for cam in data["pois"]:
            info = loads(cam["info"])

            if not info:
                info = {}

            vmax = cam["vmax"] if "vmax" in cam else -1
            try:
                vmax = int(vmax)

            except ValueError:
                vmax = -1

            radars.append(RadarWarning(
                x=float(cam["lat"]),
                y=float(cam["lng"]),
                type=int(cam["type"]),
                vmax=vmax,
                is_cluster="count_cluster" in info,
            ))

        # copy cams to memory
        start = perf_counter()
        length = 0
        set_cams_event.set()
        for i, cam in enumerate(radars):
            try:
                cams[i].x = cam.x
                cams[i].y = cam.y
                cams[i].type = cam.type
                cams[i].vmax = cam.vmax
                cams[i].is_cluster = cam.is_cluster
                length = i

            except Exception as e:
                comm.send(cam.__repr__)
                comm.send(e)

        n_cams.value = length
        set_cams_event.clear()
        comm.send(f"cams took {perf_counter() - start} to copy")
        cams_updating = False

    def _update_roads() -> None:
        """
        update roads in background
        """
        nonlocal roads_updating, pos
        query = overpass_query(REQUEST_RADIUS, pos[0], pos[1])

        data = {}
        # while True:
        #     comm.send("requesting roads")
        #     try:
        #         raw_data = requests.get(
        #             OSM_BASE_URL,
        #             timeout=REQUEST_TIMEOUT,
        #             params={"data": query},
        #         )
        #
        #     except requests.exceptions.Timeout:
        #         # wait for 10 secs to not spam the api
        #         sleep(10)
        #         continue
        #
        #     comm.send("got roads")
        #
        #     try:
        #         data = raw_data.json()
        #
        #     except JSONDecodeError:
        #         # wait for 10 secs to not spam the api
        #         sleep(10)
        #         continue
        #
        #     break

        data = load(open("buffer.json", "r"))
        comm.send("got roads json")

        start = perf_counter()
        proc_roads = []
        for street in data["elements"]:
            nodes = [(p["lat"], p["lon"]) for p in street["geometry"]]
            for i in range(len(nodes) - 1):
                n1 = nodes[i]
                n2 = nodes[i + 1]

                tags = street["tags"]
                hw = tags["highway"]
                if hw in ROAD_TYPES:
                    priority = ROAD_TYPES[hw]

                else:
                    priority = 255

                # if priority >= 100:
                #     continue

                if "maxspeed" in tags:
                    vmax = tags["maxspeed"]
                    try:
                        vmax = int(vmax)

                    except ValueError:
                        if vmax in SPEED_TYPES:
                            vmax = SPEED_TYPES[vmax]

                        else:
                            print(vmax)
                            vmax = 0

                else:
                    vmax = 0

                proc_roads.append(StreetSegment(
                    ax=n1[0],
                    ay=n1[1],
                    bx=n2[0],
                    by=n2[1],
                    priority=priority,
                    vmax=vmax
                ))

        # N = len(data["elements"])
        # lat1 = np.array([pos[0]] * N, dtype=np.float64)
        # lon1 = np.array([pos[1]] * N, dtype=np.float64)
        # lat2 = np.array([road.ax for road in proc_roads], dtype=np.float64)
        # lon2 = np.array([road.ay for road in proc_roads], dtype=np.float64)
        # dxdy = np.zeros((N, 2), dtype=np.float64)
        # latlon_to_meters_batch(lat1, lon1, lat2, lon2, dxdy)
        # comm.send("np magic")

        comm.send(f"roads took {perf_counter() - start} to process")

        start = perf_counter()
        length = 0
        set_roads_event.set()
        for i, road in enumerate(proc_roads):
            roads[i].ax = road.ax
            roads[i].ay = road.ay
            roads[i].bx = road.bx
            roads[i].by = road.by
            roads[i].priority = road.priority
            roads[i].vmax = road.vmax
            length = i

        n_roads.value = length
        set_roads_event.clear()
        comm.send(f"roads took {perf_counter() - start} to copy")

    def _update_pos(t) -> None:
        """
        updates position, velocity and heading
        """
        nonlocal pos
        pos = 47.2692 - (perf_counter() - d_start) / 2000, 11.4041 - (perf_counter() - d_start) / 6000  # innsbruck

        # get velocity from last 3 positions
        dx, dy = latlon_to_meters(
            pos_cache[2].x,
            pos_cache[2].y,
            pos[0],
            pos[1],
        )
        dist = m.sqrt(dx*dx + dy*dy)
        vel = dist / (t - pos_cache[2].t)

        # set speed and heading
        curr_rot.value = m.atan2(dy, dx)#heading_degrees(
        #     pos_cache[2].x,
        #     pos_cache[2].y,
        #     pos[0],
        #     pos[1],
        # )
        curr_speed.value = vel * 3.6  # m/s to km/h

        # increment positions
        pos_cache[2] = pos_cache[1]
        pos_cache[1] = pos_cache[0]
        pos_cache[0].x = pos[0]
        pos_cache[0].y = pos[1]
        pos_cache[0].t = t

        # update position
        curr_lat.value = pos[0]
        curr_lon.value = pos[1]

        comm.send(f"{curr_speed.value}km/h, {curr_rot.value}°r")

    running = True
    comm.send("starting")
    while running:
        if quit_event.is_set():
            break

        now = perf_counter()
        # update position
        _update_pos(now)
        now_pos = latlon_to_meters(*last_update_pos, *pos)

        # update cams
        if (
                not cams_updating
                and now - last_cams_set > CAMS_UPDATE_FREQ
        ):
            # get cams
            pool.submit(_update_cams)
            last_cams_set = now

        # update streets
        dist = m.sqrt(
            now_pos[0]*now_pos[0] + now_pos[1]*now_pos[1]
        )
        if (
            not roads_updating
            and dist >= ROADS_REQUEST_RADIUS
        ):
            pool.submit(_update_roads)
            last_update_pos[0] = pos[0]
            last_update_pos[1] = pos[1]

        sleep(GPS_UPDATE_FREQ)

    end()
