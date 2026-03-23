"""
display_driver.py
23.03.2026

Driver for GC9A01 240x240 display

Author:
Nilusink
"""
from hud_lib import Color, draw_lines, draw_line, draw_circle, draw_filled_circle
from threading import Lock
import numpy as np
import mmap


def rgb255_to_bgr565(r, g, b):
    """
    Convert 8-bit RGB (0-255) to 16-bit BGR565 for displays like GC9A01.
    Args:
        r, g, b (int): Red, Green, Blue channels (0-255)
    Returns:
        int: 16-bit color in BGR565 format
    """
    # Convert 8-bit channels to 5-6-5 bits
    r5 = r >> 3
    g6 = g >> 2
    b5 = b >> 3

    # Pack in BGR565 order: BBBBB GGGGGG RRRRR
    return (b5 << 11) | (g6 << 5) | r5


class DisplayDriver:
    _width: int = 240
    _height: int = 240
    _bpp: int = 16

    def __init__(self, device_path: str = "/dev/fb1") -> None:
        fb = open(device_path, "r+b")
        fb_size = self._width * self._height * (self._bpp // 8)

        # create memory view
        self._mem = mmap.mmap(fb.fileno(), fb_size)

        # assuming self._mem is a mmap or bytearray of 240*240*2 bytes
        self._fb16 = np.frombuffer(self._mem, dtype=np.uint16)
        self._buffer16 = np.zeros_like(self._fb16, dtype=np.uint16)

        self._d_lock = Lock()
        self._b_lock = Lock()

    def get_buffer(self) -> np.ndarray:
        return self._buffer16

    def clear_screen(self) -> None:
        self._buffer16[:] = 0

    def fill_screen(self, color: Color | int, to_buffer: np.ndarray = None) -> None:
        """
        fill the screen with the given color.
        """
        if isinstance(color, Color):
            color = color.get_bgr565()

        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        buf[:] = color

        if to_buffer is None:
            self._b_lock.release()

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: int, to_buffer: np.ndarray = None) -> None:
        if (
                not 0 <= x0 < self._width
                or not 0 <= y0 < self._height
                or not 0 <= x1 < self._width
                or not 0 <= y1 < self._height
        ):
            return
        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_line(buf, self._width, x0, y0, x1, y1, color)

        if to_buffer is None:
            self._b_lock.release()

    def draw_lines(self, points: list[tuple[int, int]], color: int, to_buffer: np.ndarray = None) -> None:
        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_lines(buf, self._width, points, color)

        if to_buffer is None:
            self._b_lock.release()

    def draw_circle(
            self,
            cx: int,
            cy: int,
            radius: int,
            color: int,
            to_buffer: np.ndarray = None
    ) -> None:
        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_circle(buf, self._width, cx, cy, radius, color)

        if to_buffer is None:
            self._b_lock.release()

    def draw_filled_circle(
            self,
            cx: int,
            cy: int,
            radius: int,
            color: int,
            to_buffer: np.ndarray = None
    ) -> None:
        if (
                cx + radius > self._width
                or cy + radius > self._height
                or cx - radius < 0
                or cy - radius < 0
        ):
            return

        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_filled_circle(buf, self._width, cx, cy, radius, color)

        if to_buffer is None:
            self._b_lock.release()

    def update(self) -> None:
        self._d_lock.acquire()
        np.copyto(self._fb16, self._buffer16)
        self._d_lock.release()

    def transmit_buffer(self, from_buffer: np.ndarray) -> None:
        self._b_lock.acquire()
        np.copyto(self._buffer16, from_buffer)
        self._b_lock.release()
