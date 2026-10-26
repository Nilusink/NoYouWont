from multiprocessing import shared_memory, Event, Value, Process, Pipe
from concurrent.futures import ThreadPoolExecutor
from time import sleep, perf_counter
from PIL import Image
import numpy as np
import math as m
import ctypes

from hud_lib import MAX_CAMS, MAX_ROADS, road_t, speedcam_t, SCREEN_RADIUS, \
    latlon_to_meters, meters_to_pixels, get_detail, get_radius, \
    Vec2, Color, normalize_angle
from data_source import start_data_source
from display_driver import DisplayDriver


EMULATE_DISPLAY: bool = True
MAP_INTERVAL: float = 2
DOT_SIZE: int = 10
BUFFER_SIZE_FAC = 1.5
CAM_WARN_RANGE_SECS = 60
CAM_CRIT_RANGE_SECS = 10
CAM_CRIT_ANGLE = 0.4363323129985824


WHITE = Color().from_1(1, 1, 1).get_bgr565()
BLACK = Color().from_1(0, 0, 0).get_bgr565()
car_color = Color().from_1(0, 1, 1).get_bgr565()
bg_color = BLACK
road_color = WHITE
warn_color = Color().from_1(.5, .1, .1).get_bgr565()
shadow_color = Color().from_1(.4, .3, .2).get_bgr565()
special_color = Color().from_1(1, .6, .6).get_bgr565()
sign_red = Color().from_1(1, 0, 0).get_bgr565()

cam_stationary = Color().from_1(.8, .4, 0).get_bgr565()
cam_mobile = Color().from_1(1, 0, 0).get_bgr565()
cam_redlight = Color().from_hex("C29E4A").get_bgr565()

CONN_STATE_NET: np.uint64 = np.uint32(0b0001)
CONN_STATE_GPS: np.uint64 = np.uint32(0b0010)


def load_image(path: str) -> np.ndarray:
    img = np.array(Image.open(path).convert("RGB"), dtype=np.uint16)

    # convert to bgr565
    return (
        (img[..., 2] >> 3) |
        ((img[..., 1] >> 2) << 5) |
        ((img[..., 0] >> 3) << 11)
    )


CONN_ICON = load_image("icons/link.png")
NCONN_ICON = load_image("icons/plug-connection.png")
GPS_ICON = load_image("icons/marker.png")
NGPS_ICON = load_image("icons/compass-slash.png")


def draw_speed_sign(d: DisplayDriver, speed_limit: int) -> None:
    """
    draw a speed limit sign
    """
    d.clear_screen()
    d.draw_filled_circle(
        d.buffer_width // 2,
        d.buffer_height // 2,
        d.width // 2,
        WHITE,
    )
    d.draw_circle(
        d.buffer_width // 2,
        d.buffer_height // 2,
        d.width // 2,
        24,
        sign_red,
    )
    d.draw_digits_big(
        d.buffer_width // 2,
        d.buffer_height // 2,
        str(speed_limit),
        BLACK,
        center_text=True,
        font_size=96
    )
    d.update(
        d.buffer_width // 2,
        d.buffer_height // 2,
    )


def draw_ui(
        d: DisplayDriver,
        cam_critical: int,
        speed: int,
        speed_color,
        gps_status: bool,
        network_status: bool
) -> None:
    """
    Draws little icons

    Args:
        d: display driver
        cam_critical: speed of critical cam, 0 if none
        speed: speed in km/h
        speed_color: color of speed indicator
        gps_status: is gps connected
        network_status: is network connected

    """
    # draw speed limit
    if cam_critical:
        # speed limit 255 == -1 == variable cam
        d.draw_digits_big(
            d.width // 2,
            int(d.height * .1),
            "v" if cam_critical == 255 else str(cam_critical),
            WHITE,
            center_text=True,
            direct=True,
            font_size=48,
            background=True,
            background_color=BLACK,
            background_margin=2
        )

    # draw speed
    d.draw_digits_big(
        d.width // 2,
        int(d.height * .9),
        str(int(speed)),
        speed_color,
        center_text=True,
        direct=True,
        font_size=48,
        background=True,
        background_color=BLACK,
        background_margin=2
    )

    # draw connection status
    # d.draw_rect(
    #     0,
    #     d.height // 3 - 5,
    #     d.width // 5,  # 48
    #     d.height // 3 + 10,
    #     Color().from_1(.1, .1, .1).get_bgr565(),
    #     direct=True
    # )
    d.draw_image(
        28, 2 * d.height // 5,
        CONN_ICON if network_status else NCONN_ICON,
        direct=True,
        center=True
    )
    d.draw_image(
        28, 3 * d.height // 5,
        GPS_ICON if gps_status else NGPS_ICON,
        direct=True,
        center=True
    )


def main():
    if EMULATE_DISPLAY:
        display = DisplayDriver(
            buffer_size_factor=BUFFER_SIZE_FAC,
            device_path="./disp_fb.bin",
            emulate_device_buffer=True
        )

    else:
        display = DisplayDriver(
            buffer_size_factor=BUFFER_SIZE_FAC
        )

    # populate icons

    # create fancy process stuff
    parent_com, child_com = Pipe()

    road_size = ctypes.sizeof(road_t)
    cam_size = ctypes.sizeof(speedcam_t)

    road_shm = shared_memory.SharedMemory(create=True, size=road_size * MAX_ROADS)
    cam_shm = shared_memory.SharedMemory(create=True, size=cam_size * MAX_CAMS)

    pixel_offset = (
        (display.buffer_width - display.width) // 2,
        (display.buffer_height - display.height) // 2
    )
    buffer_min_x = 0
    buffer_min_y = 0
    buffer_max_x = display.buffer_width
    buffer_max_y = display.buffer_height

    cams_event = Event()
    roads_event = Event()
    quit_event = Event()

    num_roads = Value("I", 0, lock=False)
    num_cams = Value("I", 0, lock=False)
    flags = Value("I", 0, lock=False)
    # conn state: 0=network, 1=GPS

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
        "flags": flags,
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
        nonlocal roads_updating, roads, radius, lat, lon, latc, lonc
        roads_updating = True
        to_draw = []
        to_shadow = []
        to_warn = []
        special = []

        detail_level = get_detail(radius)
        start = perf_counter()
        try:
            # reset map buffer
            map_update_buffer[:] = 0

            # calculate roads
            for i in range(num_roads.value):
                line = roads[i]

                x1, y1 = latlon_to_meters(
                    line.ax,
                    line.ay,
                    latc,
                    lonc
                )
                x2, y2 = latlon_to_meters(
                    line.bx,
                    line.by,
                    latc,
                    lonc
                )

                p1 = meters_to_pixels(
                    x1,
                    y1,
                    0,
                    0,
                    radius * BUFFER_SIZE_FAC,
                    display.buffer_width,
                )

                p2 = meters_to_pixels(
                    x2,
                    y2,
                    0,
                    0,
                    radius * BUFFER_SIZE_FAC,
                    display.buffer_width,
                )

                if (
                    not buffer_min_x <= p1[0] <= buffer_max_x
                    or not buffer_min_y <= p1[1] <= buffer_max_y
                    or not buffer_min_x <= p2[0] <= buffer_max_x
                    or not buffer_min_y <= p2[1] <= buffer_max_y
                ):
                    continue

                if line.vmax > 0:
                    # if (line.vmax + 10) * 1.1 >= speed or line.priority == 0:
                    if line.vmax * 1.10 >= speed:
                        to_draw.append((p1, p2))

                    # 3% speed tolerance & +50kmh for loosing your license
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

            # calculate cams
            if max_speed > 50:
                updated_stationary_cams.clear()
                updated_mobile_cams.clear()
                updated_redlight_cams.clear()
                updated_unknowns.clear()

                for i in range(num_cams.value):
                    cam = cams[i]

                    x, y = latlon_to_meters(
                        cam.x,
                        cam.y,
                        latc,
                        lonc
                    )

                    pos = meters_to_pixels(
                        x, y,
                        0, 0,
                        radius * BUFFER_SIZE_FAC,
                        display.buffer_width,
                    )
                    pos = (*pos, cam.vmax)

                    if m.sqrt(x*x + y*y) > radius*1.6:
                        continue

                    if cam.type == 2 or cam.type == 11 or cam.type == 111:
                        updated_redlight_cams.append(pos)

                    elif cam.type <= 12:
                        updated_mobile_cams.append(pos)

                    elif cam.type >= 100:
                        updated_stationary_cams.append(pos)

                    else:
                        # unknowns, probably construction site / accident
                        updated_unknowns.append(pos)

                # print(f"{i=}")
                # print(f"{len(cluster_cams)=}")
                # print(f"{len(stationary_cams)=}")
                # print(f"{len(mobile_cams)=}")

            # draw roads
            for line in to_draw:
                display.draw_line(*line[0], *line[1], road_color, to_buffer=map_update_buffer)

            for line in to_shadow:
                display.draw_line(*line[0], *line[1], shadow_color, to_buffer=map_update_buffer)

            for line in to_warn:
                display.draw_line(*line[0], *line[1], warn_color, to_buffer=map_update_buffer)

            for line in special:
                display.draw_line(*line[0], *line[1], special_color, to_buffer=map_update_buffer)

            # update screen buffer
            roads_updating = False

        except Exception as e:
            print(e)
            raise e

    # wait for position
    print("waiting for position")
    display.fill_screen(bg_color)
    c = 0
    while curr_lat.value == 0 and curr_lon.value == 0:
        c = (c + 1) % 4

        display.clear_screen()
        display.draw_text(
            display.buffer_width // 2, display.buffer_height // 2,
            "Waiting for position " + "." * c + (3 - c) * " ",
            WHITE,
            center_text=True
        )
        display.update(
            pivot_x=display.buffer_width // 2, pivot_y=display.buffer_height // 2
        )
        sleep(.5)

    display.clear_screen()
    display.draw_text(
        display.buffer_width // 2, display.buffer_height // 2,
        f"position found",
        WHITE,
        center_text=True
    )
    display.update(
        pivot_x=display.buffer_width // 2, pivot_y=display.buffer_height // 2
    )
    print(f"found pos: {curr_lat.value}, {curr_lon.value}")
    sleep(1)

    # wait for data_source to get first data
    print("waiting for initial data")
    display.fill_screen(bg_color)
    c = 0
    while not (
        num_roads.value > 0
    ):
        c = (c + 1) % 4

        display.clear_screen()
        display.draw_text(
            display.buffer_width // 2, display.buffer_height // 2,
            "Waiting for data " + "." * c + (3 - c) * " ",
            WHITE,
            center_text=True
        )
        display.update(
            pivot_x=display.buffer_width // 2, pivot_y=display.buffer_height // 2
        )

        while parent_com.poll(0):
            msg = parent_com.recv()
            print(f"child> {msg}")

        sleep(.5)

    display.clear_screen()
    display.update(
        pivot_x=display.buffer_width // 2, pivot_y=display.buffer_height // 2
    )
    print(num_roads.value, num_cams.value)
    print("done waiting")

    ocenter = Vec2()
    max_speed = 0
    radius = 0
    latc = 0
    lonc = 0

    stationary_cams = []
    updated_stationary_cams = []
    mobile_cams = []
    updated_mobile_cams = []
    redlight_cams = []
    updated_redlight_cams = []

    unknowns = []
    updated_unknowns = []

    pivot = Vec2()
    n_loop = 0
    while True:
        try:
            start = perf_counter()

            # wait if either of the data is being written
            while roads_event.is_set():
                sleep(.01)

            while cams_event.is_set():
                sleep(.01)

            speed = curr_speed.value
            curr_speed_kmh = (speed / 3.6)
            if speed > max_speed:
                max_speed = speed


            # zoom out if GPS signal is lost
            if flags & CONN_STATE_GPS:
                radius = get_radius(speed, 500)
                # radius = 7000

            else:
                radius = 3000

            rot = normalize_angle(-m.pi / 2 - curr_rot.value)
            meter_to_pixel_factor = (display.width / (2 * radius))

            # calculate position stuff
            lat, lon = curr_lat.value, curr_lon.value

            # draw roads to buffer
            if not roads_updating:
                np.copyto(current_map_buffer, map_update_buffer)
                latc, lonc = lat, lon
                stationary_cams = updated_stationary_cams.copy()
                mobile_cams = updated_mobile_cams.copy()
                redlight_cams = updated_redlight_cams.copy()
                unknowns = updated_unknowns.copy()
                pool.submit(update_roads)

            # draw roads from buffer
            display.clear_screen()
            display.transmit_buffer(current_map_buffer)

            # draw speed cams
            # print(f"{len(cluster_cams)=}")
            # print(f"{len(stationary_cams)=}")
            # print(f"{len(mobile_cams)=}")
            # if n_loop % 12 < 6:
                # for cam in cluster_cams:
                #     display.draw_filled_circle(
                #         cam[0],
                #         cam[1],
                #         DOT_SIZE * 2,
                #         cam_cluster
                #     )

            for cam in redlight_cams:
                display.draw_filled_circle(
                    cam[0],
                    cam[1],
                    int(2 * DOT_SIZE / 3),
                    cam_redlight
                )

            if n_loop % 6 < 3:
                for cam in stationary_cams:
                    display.draw_filled_circle(
                        cam[0],
                        cam[1],
                        DOT_SIZE,
                        cam_stationary
                    )

            if n_loop % 2 < 1:
                for cam in mobile_cams:
                    display.draw_filled_circle(
                        cam[0],
                        cam[1],
                        DOT_SIZE,
                        cam_mobile
                    )

                for cam in unknowns:
                    display.draw_filled_circle(
                        cam[0],
                        cam[1],
                        int(2 * DOT_SIZE / 3),
                        cam_redlight
                    )

            # calculate driven since last map update
            # off_meters = latlon_to_meters(lat, lon, latc, lonc)
            # off_pixels = (
            #     off_meters[0] * meter_to_pixel_factor,
            #     -(off_meters[1] * (display.width / (2 * radius)))  # idk why mirror
            # )

            # draw "car"
            pivot.x = display.buffer_width // 2  # + off_pixels[0]
            pivot.y = display.buffer_height // 2  # + off_pixels[1]

            display.draw_filled_circle(
                int(pivot.x),
                int(pivot.y),
                5,
                car_color
            )

            # check cams in warning range
            warn_range = curr_speed_kmh * CAM_WARN_RANGE_SECS
            warn_range *= meter_to_pixel_factor

            crit_range = curr_speed_kmh * CAM_CRIT_RANGE_SECS
            crit_range *= meter_to_pixel_factor

            b = Vec2().from_polar(rot - m.pi / 2 + CAM_CRIT_ANGLE, crit_range)
            c = Vec2().from_polar(rot - m.pi / 2 - CAM_CRIT_ANGLE, warn_range)
            cen = pivot + Vec2().from_polar(rot - m.pi / 2, 50)

            p = Vec2()
            cam_critical = None  # distance < 500m
            left = normalize_angle(c.angle)
            right = normalize_angle(b.angle)
            for cam in [*stationary_cams, *mobile_cams]:
                p.x = cam[0]
                p.y = cam[1]
                delta = pivot - p
                cam_angle = normalize_angle(delta.angle + m.pi)
                if delta.length <= warn_range and left <= cam_angle <= right:
                    if cam_critical:
                        if cam_critical[1] > delta.length:
                            cam_critical = (cam, delta.length, cam_angle)

                    else:
                        cam_critical = (cam, delta.length, cam_angle)

            # draw radar warnings (if in cone)
            skip_update = False
            speed_text_color = WHITE
            if cam_critical:
                # slow orange warn
                if cam_critical[1] > crit_range*2:
                    speed_limit = cam_critical[0][2]
                    if speed > speed_limit * 1.03:  # 3% speed tolerance
                        speed_text_color = cam_stationary

                    if n_loop % 6 < 3:
                        display.draw_circle(
                            int(cen.x),
                            int(cen.y),
                            display.width // 2,
                            10,
                            cam_stationary
                        )

                # faster, thicker red warn
                elif cam_critical[1] > crit_range:
                    speed_limit = cam_critical[0][2]
                    if speed > speed_limit * 1.03:  # 3% speed tolerance
                        speed_text_color = sign_red

                    if n_loop % 4 < 2:
                        display.draw_circle(
                            int(cen.x),
                            int(cen.y),
                            display.width // 2,
                            20,
                            sign_red
                        )

                # cam in 10s, big red warn / speed sign
                else:
                    if n_loop % 3 < 2:
                        speed_limit = cam_critical[0][2]

                        # if speed > vmax, draw speed sign, else red rim
                        if speed > speed_limit * 1.03:  # 3% speed tolerance
                            speed_text_color = sign_red
                            draw_speed_sign(display, speed_limit)
                            skip_update = True

                        else:
                            display.draw_circle(
                                int(cen.x),
                                int(cen.y),
                                display.width // 2,
                                20,
                                sign_red
                            )

            if not skip_update:
                display.update(
                    pivot_x=pivot.x,
                    pivot_y=pivot.y,
                    offset_y=50,
                    angle_rad=-rot
                )

                # draw user interface
                draw_ui(
                    display,
                    int(cam_critical[0][2]) if cam_critical else 0,
                    speed,
                    speed_text_color,
                    flags & CONN_STATE_GPS,
                    flags & CONN_STATE_NET,
                )

                # check for too-fast updates
                end = perf_counter()
                if (end - start) < .2:
                    sleep(.2 - (end-start))

            # print child process output
            while parent_com.poll(0):
                msg = parent_com.recv()
                print(f"child> {msg}")

            n_loop += 1
            # print(cam_critical)
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
