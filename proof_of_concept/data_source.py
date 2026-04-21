"""
data_source.py
22.03.2026

Requests data from osm and atudo for use in the main process

Author:
Nilusink
"""
from multiprocessing import shared_memory, Event, Value
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError, loads
from time import perf_counter, sleep
from dataclasses import dataclass
from traceback import print_exc
import geopandas as gpd
import math as m
import requests
import ctypes
import os

from auto_file_backup import main as backup_files


os.environ["OGR_INTERLEAVED_READING"] = "YES"

# select GPS provider
import gpsd
# from dummy_gpsd import gpsd


from hud_lib import road_t, speedcam_t, MAX_ROADS, MAX_CAMS, REQUEST_RADIUS, \
    REQUEST_TIMEOUT, CAMS_UPDATE_FREQ, ROADS_REQUEST_RADIUS, SPEED_TYPES, \
    ROAD_TYPES, position_point_t, GPS_UPDATE_FREQ, latlon_to_meters, \
    Vec2


# cam constants
MOBILE_TYPE = "0,1,2,3,4,5,6"
FIXED_TYPE = "101,102,103,104,105,106,107,108,109,110,111,112,113,114,115"


# road constants
STREET_TYPES = [
    "motorway", "trunk", "primary", "secondary",
    "tertiary", "residential", "unclassified",
    "service", "living_street"
]

DEBUG_FILE = f"./logs/gps_debug_{perf_counter()}.csv"


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


class BBox:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def __init__(
            self,
            lat_min: float,
            lat_max: float,
            lon_min: float,
            lon_max: float
        ) -> None:
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """:returns: lat_min, lon_min, lat_max, lon_max"""
        return self.lat_min, self.lon_min, self.lat_max, self.lon_max

    @property
    def ibbox(self) -> tuple[float, float, float, float]:
        """:returns: lon_min, lat_min, lon_max, lat_max"""
        return self.lon_min, self.lat_min, self.lon_max, self.lat_max


def atudo_url(get_type: str, bbox: str) -> str:
    return f"https://cdn2.atudo.net/api/1.0/vl.php?type={get_type}&box={bbox}"


def bounding_box(lat_center: float, lon_center: float, radius_m: float) -> BBox:
    """
    Returns a bounding box around (lat_center, lon_center) with a radius in meters.
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

    return BBox(lat_min, lat_max, lon_min, lon_max)


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
    global DEBUG_FILE

    d_start = perf_counter()

    comm.send("0")
    # make sure events are cleared
    set_roads_event.clear()
    set_cams_event.clear()
    curr_lat.value = 0  # start in umhausen
    curr_lon.value = 0
    curr_rot.value = 0

    # setup gps
    gpsd.connect()

    # wait for actual data
    pos = (0, 0)  # gps position as coordinates
    while True:
        frame = gpsd.get_current()
        if frame.mode < 2:
            continue

        curr_lat.value = frame.lat
        curr_lon.value = frame.lon
        pos = (frame.lat, frame.lon)
        break

    roads_shm = shared_memory.SharedMemory(name=roads_memory_name)
    cams_shm = shared_memory.SharedMemory(name=cams_memory_name)

    cams_updating = False
    roads_updating = False

    last_cams_set = 0
    last_update_pos = [0, 0]  # position as meters

    pool = ThreadPoolExecutor(max_workers=3)
    roads = (road_t * MAX_ROADS).from_buffer(roads_shm.buf)
    cams = (speedcam_t * MAX_CAMS).from_buffer(cams_shm.buf)

    # start file backup
    comm.send("starting file backup")
    pool.submit(backup_files)

    pos_cache = (position_point_t * 3)()
    last_vel_update = d_start
    last_file_bup = d_start

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
            [str(v) for v in bounding_box(pos[0], pos[1], REQUEST_RADIUS).bbox]
        )

        url = atudo_url(get_type, bbox)

        # try and get data until its working
        data = {}
        while True:
            try:
                comm.send(f"requesting cams")
                raw_data = requests.get(url, timeout=REQUEST_TIMEOUT)

            except requests.exceptions.Timeout:
                comm.send("cam timeout")
                # wait for 10 secs to not spam the api
                sleep(10)
                continue

            try:
                data = raw_data.json()

            except JSONDecodeError:
                comm.send("json error")
                # wait for 10 secs to not spam the api
                sleep(10)
                continue

            break

        comm.send("got cams")

        # data = load(open("cam_data.json", "r"))

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

        start = perf_counter()
        comm.send("loading file")
        raw_roads = gpd.read_file(
            "roads_europe.gpkg",
            layer="lines",
            engine="pyogrio",
            bbox=bounding_box(pos[0], pos[1], REQUEST_RADIUS).ibbox,
        )
        comm.send(f"loading took {perf_counter()-start:.1f}s")

        comm.send("parsing tags")
        # fill other tags
        raw_roads["access"] = raw_roads["other_tags"].str.extract(
            r'access=([^,|"]+)', expand=False
        )
        raw_roads["access"] = raw_roads["access"].fillna("unknown")
        raw_roads["motor_vehicle"] = raw_roads["other_tags"].str.extract(
            r'motor_vehicle=([^,|"]+)', expand=False
        )
        raw_roads["motor_vehicle"] = raw_roads["motor_vehicle"].fillna("unknown")
        raw_roads["maxspeed"] = raw_roads["other_tags"].str.extract(
            r'maxspeed:type"=>"([^"]+)"', expand=False
        )

        comm.send("filtering")
        # filter road types
        road_nodes = raw_roads[
            raw_roads["highway"].isin(STREET_TYPES)
            & (raw_roads["access"].isna() | ~raw_roads["access"].isin(["private", "no"]))
            & (raw_roads["motor_vehicle"].isna() | (raw_roads["motor_vehicle"] != "no"))
        ]

        # data = load(open("buffer.json", "r"))
        comm.send("got roads json")

        try:
            start = perf_counter()
            proc_roads = []
            for _, street in road_nodes.iterrows():
                line = street.geometry

                nodes = list(line.coords)  # (x, y) = (lon, lat)
                for i in range(len(nodes) - 1):
                    y1, x1 = nodes[i]
                    y2, x2 = nodes[i + 1]

                    hw = street["highway"]
                    if hw in ROAD_TYPES:
                        priority = ROAD_TYPES[hw]

                    else:
                        priority = 255

                    if street["maxspeed"]:
                        vmax = street["maxspeed"]
                        try:
                            vmax = int(vmax)

                        except ValueError:
                            if vmax in SPEED_TYPES:
                                vmax = SPEED_TYPES[vmax]

                            else:
                                vmax = 0

                    else:
                        vmax = 0

                    proc_roads.append(StreetSegment(
                        ax=x1,
                        ay=y1,
                        bx=x2,
                        by=y2,
                        priority=priority,
                        vmax=vmax
                    ))

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

        except Exception as e:
            comm.send(e, "err")
            print_exc()

    def _update_pos(t) -> None:
        """
        updates position, velocity and heading
        """
        nonlocal pos, last_vel_update

        # read position from sensor
        packet = gpsd.get_current()

        # require at lease 2d lock
        if packet.mode < 2:
            with open(DEBUG_FILE, "a") as f:
                f.write(f"{t},{packet.mode},,,,\n")
            return

        pos = packet.lat, packet.lon

        # print(packet.lat, packet.lon, packet.mode)

        # get velocity from last 3 positions
        dx, dy = latlon_to_meters(
            pos_cache[2].x,
            pos_cache[2].y,
            pos[0],
            pos[1],
        )
        vel = packet.speed()

        # set speed and heading
        if vel > .5:
            ang = m.atan2(dy, dx)
            if ang != 0:
                curr_rot.value = ang

        if vel > .1:
            curr_speed.value = vel * 3.6  # m/s to km/h
            last_vel_update = perf_counter()

        with open(DEBUG_FILE, "a") as f:
            f.write(f"{t},{packet.mode},{pos[0]},{pos[1]},{curr_speed.value},{curr_rot.value}\n")

        # increment positions
        pos_cache[2] = pos_cache[1]
        pos_cache[1] = pos_cache[0]
        pos_cache[0].x = pos[0]
        pos_cache[0].y = pos[1]
        pos_cache[0].t = t

        # update position
        curr_lat.value = pos[0]
        curr_lon.value = pos[1]

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

        # upload files if standing for longer than 30 seconds
        # and there is more than 10 minutes of drive data
        if last_vel_update - last_file_bup > 60*10 and now - last_vel_update > 30:
            # create new file
            DEBUG_FILE = f"./logs/gps_debug_{now}.csv"
            pool.submit(backup_files)

        sleep(GPS_UPDATE_FREQ)

    end()


if __name__ == "__main__":
    road_size = ctypes.sizeof(road_t)
    cam_size = ctypes.sizeof(speedcam_t)

    class comm:
        def send(self, *msg):
            print(*msg)

    x = shared_memory.SharedMemory(create=True, size=road_size * MAX_ROADS)
    y = shared_memory.SharedMemory(create=True, size=cam_size * MAX_CAMS)

    start_data_source(
        Event(),
        Event(),
        Event(),
        x.name,
        y.name,
        Value("I", 0, lock=False),
        Value("I", 0, lock=False),
        Value("f", 0, lock=True),
        Value("f", 0, lock=True),
        Value("f", 0, lock=True),
        Value("f", 0, lock=True),
        comm()
    )
