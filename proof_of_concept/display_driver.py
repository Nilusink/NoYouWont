"""
display_driver.py
23.03.2026

Driver for GC9A01 240x240 display

Author:
Nilusink
"""
from hud_lib import Color, draw_lines, draw_line, draw_circle, draw_filled_circle, \
    draw_char
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


def rotate_buffer16(src_buf, dst_buf, width, height, angle_rad):
    """
    src_buf:  flat uint16 array (source image)
    dst_buf:  flat uint16 array (output framebuffer)
    width, height: dimensions
    angle_rad: rotation angle in radians
    """

    # reshape to 2D views (no copy)
    src = src_buf.reshape((height, width))
    dst = dst_buf.reshape((height, width))

    cx = (width - 1) / 2.0
    cy = (height - 1) / 2.0

    # coordinate grid
    y, x = np.indices((height, width), dtype=np.float32)

    x -= cx
    y -= cy

    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    # inverse rotation
    src_x = x * cos_a + y * sin_a + cx
    src_y = -x * sin_a + y * cos_a + cy

    # nearest neighbor
    src_x = src_x.astype(np.int32)
    src_y = src_y.astype(np.int32)

    # mask valid pixels
    valid = (
        (src_x >= 0) & (src_x < width) &
        (src_y >= 0) & (src_y < height)
    )

    # clear output
    dst.fill(0)

    # copy pixels
    dst[valid] = src[src_y[valid], src_x[valid]]


def render_rotated_view(
    big_buf, fb_buf,
    big_w, big_h,
    screen_w, screen_h,
    pivot_x, pivot_y,
    angle_rad,
    offset_x=0, offset_y=0
):
    big = big_buf.reshape((big_h, big_w))
    fb  = fb_buf.reshape((screen_h, screen_w))

    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    # screen grid
    y, x = np.indices((screen_h, screen_w), dtype=np.float32)

    # screen "center" with offset applied
    cx = (screen_w - 1) / 2.0 + offset_x
    cy = (screen_h - 1) / 2.0 + offset_y

    # shift so pivot maps to (cx, cy)
    x -= cx
    y -= cy

    # inverse rotation
    src_x = x * cos_a + y * sin_a + pivot_x
    src_y = -x * sin_a + y * cos_a + pivot_y

    src_x = src_x.astype(np.int32)
    src_y = src_y.astype(np.int32)

    valid = (
        (src_x >= 0) & (src_x < big_w) &
        (src_y >= 0) & (src_y < big_h)
    )

    fb.fill(0)
    fb[valid] = big[src_y[valid], src_x[valid]]

class DisplayDriver:
    _width: int = 240
    _height: int = 240
    _bpp: int = 16

    def __init__(
            self,
            device_path: str = "/dev/fb1",
            buffer_size_factor: float = 1
    ) -> None:
        fb = open(device_path, "r+b")
        fb_size = self._width * self._height * (self._bpp // 8)

        self._buffer_w = int(self._width * buffer_size_factor)
        self._buffer_h = int(self._height * buffer_size_factor)

        # create memory view
        self._mem = mmap.mmap(fb.fileno(), fb_size)

        # assuming self._mem is a mmap or bytearray of 240*240*2 bytes
        self._fb16 = np.frombuffer(self._mem, dtype=np.uint16)
        self._screen_buffer = np.zeros_like(self._fb16, dtype=np.uint16)
        self._buffer16 = np.zeros(self._buffer_w * self._buffer_h, dtype=np.uint16)
        self._buffer16.reshape((self._buffer_w, self._buffer_h))

        self._d_lock = Lock()
        self._b_lock = Lock()

    @property
    def width(self) -> int:
        return self._width

    @property
    def buffer_width(self) -> int:
        return self._buffer_w

    @property
    def height(self) -> int:
        return self._height

    @property
    def buffer_height(self) -> int:
        return self._buffer_h

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
                not 0 <= x0 <= self.buffer_width
                or not 0 <= y0 <= self.buffer_height
                or not 0 <= x1 <= self.buffer_width
                or not 0 <= y1 <= self.buffer_height
        ):
            return
        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_line(buf, self.buffer_width, x0, y0, x1, y1, color)

        if to_buffer is None:
            self._b_lock.release()

    def draw_lines(self, points: list[tuple[int, int]], color: int, to_buffer: np.ndarray = None) -> None:
        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_lines(buf, self.buffer_width, points, color)

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

        draw_circle(buf, self.buffer_width, cx, cy, radius, color)

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
                cx + radius > self.buffer_width
                or cy + radius > self.buffer_height
                or cx - radius < 0
                or cy - radius < 0
        ):
            return

        buf = to_buffer if to_buffer is not None else self._buffer16

        if to_buffer is None:
            self._b_lock.acquire()

        draw_filled_circle(buf, self.buffer_width, cx, cy, radius, color)

        if to_buffer is None:
            self._b_lock.release()

    def draw_char(
            self,
            x: int, y: int,
            character: int,
            color: int,
            to_buffer: np.ndarray = None
    ) -> None:
        buf = to_buffer if to_buffer is not None else self._buffer16

        draw_char(buf, self.buffer_width, x, y, character, color)

    def draw_text(
            self,
            x: int, y: int,
            text: str,
            color: int,
            to_buffer: np.ndarray = None
    ) -> None:
        buf = to_buffer if to_buffer is not None else self._buffer16

        for i in range(len(text)):
            draw_char(buf, self.buffer_width, x + i*8, y, ord(text[i]), color)

    def update(
            self,
            pivot_x: int = 0,
            pivot_y: int = 0,
            angle_rad: float = 0,
            offset_x: int = 0,
            offset_y: int = 0,
    ) -> None:
        self._d_lock.acquire()

        self._screen_buffer[:] = 0
        render_rotated_view(
            self._buffer16,
            self._screen_buffer,
            self._buffer_w,
            self._buffer_h,
            self._width,
            self._height,
            pivot_x, pivot_y, angle_rad, offset_x, offset_y
        )
        np.copyto(self._fb16, self._screen_buffer)

        self._d_lock.release()

    def transmit_buffer(
            self,
            from_buffer: np.ndarray,
            rotate_by: float = 0
    ) -> None:
        """
        copy buffer to current frame buffer and rotate by x
        """
        self._b_lock.acquire()
        if rotate_by != 0:
            rotate_buffer16(from_buffer, self._buffer16, self._width, self._height, rotate_by)

        else:
            np.copyto(self._buffer16, from_buffer)

        self._b_lock.release()
