from OpenGL.GL import glClearColor, glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, \
    glColor4f, glEnableClientState, GL_VERTEX_ARRAY, glVertexPointer, GL_FLOAT, \
    glDrawArrays, GL_LINES, glDisableClientState
from dataclasses import dataclass
import pygame as pg
import math as m
import numpy as np
import time
import json

from render_bindings import renderer, Vec2, Color


@dataclass(frozen=True)
class RadarWarning:
    pos: Vec2  # in meters
    type: int
    info: dict
    vmax: int


@dataclass(frozen=True)
class StreetSegment:
    a: Vec2
    b: Vec2
    priority: int
    vmax: int


def get_osm_data() -> list:
    data = json.load(open("buffer.json", "r"))
    return data["elements"]


def get_cam_data() -> list:
    data = json.load(open("cam_data.json", "r"))
    return data["pois"]


def draw_roads_pointer(roads, color: Color):
    vertices = np.array(
        [coord for seg in roads for point in seg for coord in point],
        dtype=np.float32
    )

    glColor4f(*color.rgba1)
    glEnableClientState(GL_VERTEX_ARRAY)
    glVertexPointer(2, GL_FLOAT, 0, vertices)
    glDrawArrays(GL_LINES, 0, len(vertices)//2)
    glDisableClientState(GL_VERTEX_ARRAY)


lat, lon = 47.2612, 11.3341
RADIUS = 3000  # 5 km
screen_radius = 120
dot_size = 3


def latlon_to_meters(lat1, lon1, lat2, lon2):
    """Returns approximate x, y in meters from point1 to point2"""
    R = 6371000  # Earth radius in meters
    dx = (lon2 - lon1) * m.cos(m.radians(lat1)) * (2 * m.pi * R / 360)
    dy = (lat2 - lat1) * (2 * m.pi * R / 360)
    return dx, dy


def meters_to_pixels(dx, dy, cx, cy, radius, screen_size):
    scale = screen_size / (2 * radius)  # pixels per meter
    px = screen_size / 2 + (dx + cx) * scale   # center at middle
    py = screen_size / 2 - (dy + cy) * scale   # invert y to have north up
    return px, py


def latlon_to_pixel(lat, lon, lat_center, lon_center, radius_m, screen_size):
    dx, dy = latlon_to_meters(lat_center, lon_center, lat, lon)
    return meters_to_pixels(dx, dy, radius_m, screen_size)


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


def get_roads(
        street_data
) -> list[StreetSegment]:
    roads = []

    for street in street_data:
        nodes = []
        for point in street["geometry"]:
            x, y = latlon_to_meters(
                point["lat"],
                point["lon"],
                lat,
                lon,
            )

            nodes.append(Vec2().from_cartesian(x, y))
            # nodes.append((x, y))

        for i in range(len(nodes) - 1):
            n1 = nodes[i]
            n2 = nodes[i+1]

            tags = street["tags"]
            hw = tags["highway"]
            if hw in ROAD_TYPES:
                priority = ROAD_TYPES[hw]

            else:
                priority = 300

            if "maxspeed" in tags:
                vmax = int(tags["maxspeed"])
                # print(hw, street["tags"])

            else:
                vmax = -1

            roads.append(StreetSegment(
                a=n1,
                b=n2,
                priority=priority,
                vmax=vmax
            ))

    return roads


def get_cams(cam_data) -> list[RadarWarning]:
    radars = []
    for cam in cam_data:
        pos = latlon_to_meters(
            float(cam["lat"]),
            float(cam["lng"]),
            lat,
            lon,
        )

        info = json.loads(cam["info"])

        if not info:
            info = {}

        radars.append(RadarWarning(
            pos=Vec2().from_cartesian(*pos),
            type=int(cam["type"]),
            info=info,
            vmax=cam["vmax"] if "vmax" in cam else -1,
        ))

    return radars


def get_detail(radius: float) -> float:
    return 20 * ((500/radius) ** 1.285)


def get_radius(speed: float) -> float:
    return 100 + 3200 / (1 + (100 / speed) ** 2.5)


def offset_center(lat, lon, rotation, radius) -> tuple[float, float]:
    """
        Offset a lat/lon by `radius` meters in direction `rotation` (degrees).

        lat, lon: degrees
        rotation: degrees (0 = north, 90 = east)
        radius: meters
        """
    R = 6371000  # Earth radius (m)

    lat1 = m.radians(lat)
    lon1 = m.radians(lon)

    # Convert your rotation → geographic bearing
    bearing = (m.pi / 2) - rotation

    d = radius / R

    lat2 = m.asin(
        m.sin(lat1) * m.cos(d) +
        m.cos(lat1) * m.sin(d) * m.cos(bearing)
    )

    lon2 = lon1 + m.atan2(
        m.sin(bearing) * m.sin(d) * m.cos(lat1),
        m.cos(d) - m.sin(lat1) * m.sin(lat2)
    )

    return m.degrees(lat2), m.degrees(lon2)


def main():
    global RADIUS
    pg.init()
    renderer.init("ui test", screen_radius)

    street_data = get_osm_data()
    cam_data = get_cam_data()

    roads = get_roads(street_data)
    cams = get_cams(cam_data)

    cc = Vec2().from_cartesian(
        renderer.window_size[0]/2,
        renderer.window_size[1]/2
    )
    speed = 1

    ocenter = Vec2()
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return

            elif event.type == pg.MOUSEWHEEL:
                # RADIUS *= 1 + event.y / 10
                speed = max([
                    1,
                    speed + event.y * 10
                ])
                print(speed)
                # print(
                #     speed,
                #     get_radius(speed),
                #     get_detail(get_radius(speed)),
                # )

        mouse_pos = Vec2().from_cartesian(*pg.mouse.get_pos())
        delta = cc - mouse_pos

        # radius = 500 + RADIUS/2 + RADIUS/2 * m.sin(time.time() / 5)
        radius = get_radius(speed)
        # radius = RADIUS
        # rot = ((time.time() / 3) % m.pi * 2)
        rot = -m.pi / 2 - delta.angle

        latc, lonc = latlon_to_meters(
            *offset_center(lat, lon, m.pi/2, radius/2.5),
            lat, lon
        )
        ocenter.x = latc
        ocenter.y = lonc
        ocenter.angle = -rot + m.pi/2

        glClearColor(0.0, 0.0, 0.3, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        detail_level = get_detail(radius)

        # draw
        ## create display
        renderer.start_stencil(True)
        renderer.draw_circle(
            (screen_radius, screen_radius),
            screen_radius,
            64,
            Color().from_1(0, 0, 0)
        )
        renderer.enable_stencil(True)

        ## on display
        to_draw = []
        to_shadow = []
        to_warn = []
        special = []
        for line in roads:
            dist = min([
                (line.a - ocenter).length,
                (line.b - ocenter).length
            ])
            if dist > radius:
                continue

            tmp1 = line.a.copy()
            tmp2 = line.b.copy()

            tmp1.angle += rot
            tmp2.angle += rot

            p1 = meters_to_pixels(
                *tmp1.xy,
                latc,
                lonc,
                radius,
                screen_radius * 2
            )

            p2 = meters_to_pixels(
                *tmp2.xy,
                latc,
                lonc,
                radius,
                screen_radius * 2
            )

            if line.vmax > 0:
                # if (line.vmax + 10) * 1.1 >= speed or line.priority == 0:
                if line.vmax * 1.1 + 30 >= speed:
                    to_draw.append((p1, p2))

                elif line.vmax * 1.03 + 50 < speed:
                    if line.priority == 0:
                        special.append((p1, p2))

                    else:
                        to_warn.append((p1, p2))

                else:
                    if line.priority == 0:
                        to_draw.append((p1, p2))

                    else:
                        to_shadow.append((p1, p2))

            else:
                if line.priority <= detail_level:
                    to_draw.append((p1, p2))

                else:
                    to_shadow.append((p1, p2))

        draw_roads_pointer(to_draw, Color().from_1(.8, .8, .8))
        draw_roads_pointer(special, Color().from_1(1, .6, .6))
        draw_roads_pointer(to_shadow, Color().from_1(.3, .3, .3))
        draw_roads_pointer(to_warn, Color().from_1(.5, .1, .1))

        for cam in cams:
            pos = cam.pos.copy()
            pos.angle += rot
            pos = meters_to_pixels(pos.x, pos.y, latc, lonc, radius, screen_radius * 2)

            if "count_cluster" in cam.info:
                renderer.draw_circle(
                    pos,
                    6,
                    8,
                    Color().from_1(1, 1, 1)
                )

            elif cam.type <= 10:
                renderer.draw_circle(
                    pos,
                    dot_size,
                    8,
                    Color().from_1(1, 0, 0)
                )

            elif cam.type >= 100:
                renderer.draw_circle(
                    pos,
                    dot_size,
                    8,
                    Color().from_1(1, .5, 0)
                )

            else:
                print(cam.type)

        # draw "car"
        cen = latlon_to_meters(lat, lon, lat, lon)
        renderer.draw_circle(
            meters_to_pixels(*cen, latc, lonc, radius, screen_radius*2),
            3,
            8,
            Color().from_1(0, 1, 1)
        )

        renderer.disable_stencil()

        # update display
        pg.display.flip()


if __name__ == "__main__":
    main()
