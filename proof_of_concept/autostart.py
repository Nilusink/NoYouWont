"""
autostart.py
24.03.2026

starts with boot - shows connection state on display

Author:
Nilusink
"""
from display_driver import DisplayDriver
from hud_lib import Color
from time import sleep
import subprocess
import os


def is_network_up() -> list[str]:
    """
    gets all available network devices (besides lo)
    """
    up = []
    for file in os.listdir('/sys/class/net'):
        if file != "lo":
            if open(f"/sys/class/net/{file}/operstate").read().strip() == "up":
                up.append(file)

    return up


def get_ip(interface: str = "wlan0") -> str | None:
    """
    get device ip
    """
    result = subprocess.run(
        ["ip", "-4", "addr", "show", interface],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if "inet " in line:
            return line.strip().split()[1].split("/")[0]

    return None


def wait_connection(d: DisplayDriver, loop: bool = True) -> None:
    """
    wait for network to connect and show ip
    """
    # wait for wlan
    c = 0
    while not is_network_up():
        c = (c+1) % 4

        d.clear_screen()
        d.draw_text(
            120, 116,
            "Connecting to network " + "." * c + (3-c) * " ",
            Color().from_1(1, 1, 1).get_bgr565(),
            center_text=True
        )
        d.direct_update()

        sleep(.5)

    # get ip
    segment_height = 24
    while True:
        interfaces = is_network_up()
        ips = []
        for interface in interfaces:
            ip = get_ip(interface)
            if ip:
                ips.append(ip)

        d.clear_screen()

        if not ips:
            c = (c+1) % 4
            d.draw_text(
                120, 116,
                "Waiting for ip " + "." * c + (3-c) * " ",
                Color().from_1(1, 1, 1).get_bgr565(),
                center_text=True
            )

        else:
            for i, (ip, interface) in enumerate(zip(ips, interfaces)):
                d.draw_text(
                    120, 120 - len(ips) * (segment_height // 2) + segment_height * i,
                    f"Connected to {interface}",
                    Color().from_1(1, 1, 1).get_bgr565(),
                    center_text=True
                )
                d.draw_text(
                    120, 120 - len(ips) * (segment_height // 2) + segment_height * i + 9,
                    f"IP: {ip}",
                    Color().from_1(.5, .5, 1).get_bgr565(),
                    center_text=True
                )
        d.direct_update()

        sleep(.5)

        if ips and not loop:
            return


def main() -> None:
    """main program"""
    display = DisplayDriver()

    # wait for connection
    wait_connection(display, False)


if __name__ == "__main__":
    main()
