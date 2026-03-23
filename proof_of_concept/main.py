from multiprocessing import shared_memory, Event, Value, Process, Pipe
from concurrent.futures import ThreadPoolExecutor
from time import sleep, perf_counter
import numpy as np
import math as m
import ctypes

from hud_lib import MAX_CAMS, MAX_ROADS, road_t, speedcam_t, SCREEN_RADIUS, \
    latlon_to_meters, meters_to_pixels, offset_center, get_detail, get_radius, \
    Vec2, Color
from data_source import start_data_source
from display_driver import DisplayDriver


MAP_INTERVAL: float = 2
DOT_SIZE: int = 4


WHITE = Color().from_1(1, 1, 1)
BLACK = Color().from_1(0, 0, 0)
car_color = Color().from_1(0, 1, 1)
bg_color = BLACK
road_color = WHITE
warn_color = Color().from_1(.5, .1, .1)
shadow_color = Color().from_1(.3, .3, .3)
special_color = Color().from_1(1, .6, .6)


def main():
    display = DisplayDriver()

    # create fancy process stuff
    parent_com, child_com = Pipe()

    road_size = ctypes.sizeof(road_t)
    cam_size = ctypes.sizeof(speedcam_t)

    road_shm = shared_memory.SharedMemory(create=True, size=road_size * MAX_ROADS)
    cam_shm = shared_memory.SharedMemory(create=True, size=cam_size * MAX_CAMS)

    cams_event = Event()
    roads_event = Event()
    quit_event = Event()

    num_roads = Value("I", 0, lock=False)
    num_cams = Value("I", 0, lock=False)

    curr_lat = Value("f", 0, lock=True)
    curr_lon = Value("f", 0, lock=True)
    curr_rot = Value("f", 0, lock=True)
    curr_speed = Value("f", 0, lock=True)

    pool = ThreadPoolExecutor(max_workers=1)
    roads_updating = False

    Process(target=start_data_source, kwargs={
        "set_cams_event": cams_event,
        "set_roads_event": roads_event,
        "quit_event": quit_event,
        "roads_memory_name": road_shm.name,
        "cams_memory_name": cam_shm.name,
        "n_roads": num_roads,
        "n_cams": num_cams,
        "curr_lat": curr_lat,
        "curr_lon": curr_lon,
        "curr_rot": curr_rot,
        "curr_speed": curr_speed,
        "comm": child_com
    }).start()

    roads = (road_t * MAX_ROADS).from_buffer(road_shm.buf)
    cams = (speedcam_t * MAX_CAMS).from_buffer(cam_shm.buf)
    current_map_buffer = np.zeros_like(display.get_buffer(), dtype=np.uint16)
    map_update_buffer = np.zeros_like(display.get_buffer(), dtype=np.uint16)

    def update_roads():
        nonlocal roads_updating, roads, detail_level
        roads_updating = True
        to_draw = []
        to_shadow = []
        to_warn = []
        special = []

        try:

            # reset map buffer
            map_update_buffer[:] = 0

            print(num_roads.value)
            for i in range(num_roads.value):
                line = roads[i]

                x1, y1 = latlon_to_meters(
                    line.ax,
                    line.ay,
                    lat,
                    lon
                )
                x2, y2 = latlon_to_meters(
                    line.bx,
                    line.by,
                    lat,
                    lon
                )

                if (
                        x1 - latc > radius
                        or y1 - lonc > radius
                        or x2 - latc > radius
                        or y2 - lonc > radius
                ):
                    continue
                #
                # tmp1 = Vec2()
                # tmp2 = Vec2()
                #
                # tmp1.angle += rot
                # tmp2.angle += rot

                p1 = meters_to_pixels(
                    x1,
                    y1,
                    latc,
                    lonc,
                    radius,
                    SCREEN_RADIUS * 2
                )

                p2 = meters_to_pixels(
                    x2,
                    y2,
                    latc,
                    lonc,
                    radius,
                    SCREEN_RADIUS * 2
                )

                if line.vmax > 0:
                    # if (line.vmax + 10) * 1.1 >= speed or line.priority == 0:
                    if line.vmax * 1.12 >= speed:
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

            for line in to_draw:
                display.draw_line(*line[0], *line[1], road_color.get_bgr565(), to_buffer=map_update_buffer)

            for line in to_shadow:
                display.draw_line(*line[0], *line[1], shadow_color.get_bgr565(), to_buffer=map_update_buffer)

            for line in to_warn:
                display.draw_line(*line[0], *line[1], warn_color.get_bgr565(), to_buffer=map_update_buffer)

            for line in special:
                display.draw_line(*line[0], *line[1], special_color.get_bgr565(), to_buffer=map_update_buffer)

            # update screen buffer
            roads_updating = False
            print("map")

        except Exception as e:
            print(e)
            raise e

    # wait for data_source to get first data
    print("waiting for initial data")
    display.fill_screen(bg_color)
    x = False
    while not (
        num_roads.value > 0
        and num_cams.value > 0
    ):
        if x:
            display.draw_filled_circle(120, 120, 50, WHITE.get_bgr565())

        else:
            display.draw_filled_circle(120, 120, 50, bg_color.get_bgr565())

        display.update()

        x = not x

        print(num_roads.value, num_cams.value)
        while parent_com.poll(0):
            msg = parent_com.recv()
            print(f"child> {msg}")

        sleep(1)

    display.draw_filled_circle(120, 120, 50, bg_color.get_bgr565())
    display.update()
    print(num_roads.value, num_cams.value)
    print("done waiting")

    ocenter = Vec2()
    max_speed = 0
    last_map = 0
    while True:
        try:
            start = perf_counter()
            # wait if either of the data is being written
            while roads_event.is_set():
                sleep(.01)
            while cams_event.is_set():
                sleep(.01)

            speed = curr_speed.value
            if speed > max_speed:
                max_speed = speed

            radius = get_radius(speed)
            rot = -m.pi / 2 - curr_rot.value

            # calculate position stuff
            lat, lon = curr_lat.value, curr_lon.value
            latc, lonc = latlon_to_meters(
                *offset_center(lat, lon, m.pi/2, radius/2.5),
                lat, lon
            )
            ocenter.xy = latc, lonc
            ocenter.angle = -rot + m.pi / 2

            detail_level = get_detail(radius)

            # draw roads to buffer
            if not roads_updating:
                np.copyto(current_map_buffer, map_update_buffer)
                pool.submit(update_roads)

            # draw roads from buffer
            display.clear_screen()
            display.transmit_buffer(current_map_buffer)

            # draw speed cams
            if max_speed > 50:
                for i in range(num_cams.value):
                    cam = cams[i]

                    x, y = latlon_to_meters(
                        cam.x,
                        cam.y,
                        lat,
                        lon
                    )

                    pos = Vec2().from_cartesian(x, y)

                    # pos.angle += rot
                    pos = meters_to_pixels(
                        *pos.xy,
                        latc, lonc,
                        radius,
                        SCREEN_RADIUS * 2
                    )

                    if cam.is_cluster:
                        if 2 * start % 1 > .5:
                            display.draw_filled_circle(
                                pos[0],
                                pos[1],
                                DOT_SIZE,
                                Color().from_1(1, 1, 1).get_bgr565()
                            )
                            continue

                    elif cam.type <= 10:
                        if 4 * start % 1 > .5:
                            display.draw_filled_circle(
                                pos[0],
                                pos[1],
                                DOT_SIZE,
                                Color().from_1(1, 1, 1).get_bgr565()
                            )
                            continue

                    elif cam.type >= 100:
                        if 1.5 * start % 1 > .5:
                            display.draw_filled_circle(
                                pos[0],
                                pos[1],
                                DOT_SIZE,
                                Color().from_1(.8, .4, 0).get_bgr565()
                            )
                            continue

            # draw "car"
            cen = latlon_to_meters(lat, lon, lat, lon)
            pos = meters_to_pixels(cen[0], cen[1], latc, lonc, radius, SCREEN_RADIUS*2)
            display.draw_filled_circle(
                pos[0],
                pos[1],
                5,
                car_color.get_bgr565()
            )

            display.update()

            # print child process output
            while parent_com.poll(0):
                msg = parent_com.recv()
                print(f"child> {msg}")

            # print(perf_counter() - start)

        except KeyboardInterrupt:
            # delete memory views
            del roads, cams

            # tell data process to quit
            quit_event.set()

            # wait for data process to quit
            print("waiting for process to quit")
            while quit_event.is_set():
                sleep(.01)

            print("process has quit")

            # release memory
            road_shm.close()
            cam_shm.close()
            road_shm.unlink()
            cam_shm.unlink()

            print("quit done")
            return


if __name__ == "__main__":
    main()
