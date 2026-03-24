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


def is_wlan0_up():
    """
    check if wlan interface is up
    """
    return os.path.exists("/sys/class/net/wlan0/operstate") and \
           open("/sys/class/net/wlan0/operstate").read().strip() == "up"


def get_ip() -> str | None:
    """
    get device ip
    """
    result = subprocess.run(
        ["ip", "-4", "addr", "show", "eth0"],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if "inet " in line:
            return line.strip().split()[1].split("/")[0]

    return None


def wait_connection(d: DisplayDriver) -> None:
    """
    wait for network to connect and show ip
    """

    # wait for wlan
    c = 0
    while not is_wlan0_up():
        c = (c+1) % 4

        d.clear_screen()
        d.draw_text(
            26, 116,
            "Connecting to network " + "." * c,
            Color().from_1(1, 1, 1).get_bgr565()
        )
        d.direct_update()

        sleep(.5)

    # get ip
    ip = get_ip()

    d.clear_screen()
    d.draw_text(
        52, 108,
        "Connected to WiFi",
        Color().from_1(1, 1, 1).get_bgr565()
    )
    ip_text = "IP: " + ip
    d.draw_text(
        int((240-len(ip_text)*8)/2), 123,
        ip_text,
        Color().from_1(.5, .5, 1).get_bgr565()
    )
    d.direct_update()



def main() -> None:
    display = DisplayDriver()

    # wait for connection
    wait_connection(display)


if __name__ == "__main__":
    main()
