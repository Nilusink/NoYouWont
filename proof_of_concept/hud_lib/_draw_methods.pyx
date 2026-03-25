# cython: boundscheck=False, wraparound=False, cdivision=True
cimport cython
from libc.stdint cimport uint16_t
from ._cfonts cimport font8x8_basic, font48_digits


cdef inline void _put_pixel(uint16_t[:] fb, int width, int x, int y, uint16_t color):
    fb[y * width + x] = color


cpdef void draw_line(uint16_t[:] fb, int width, int x0, int y0, int x1, int y1, uint16_t color):
    cdef int dx = abs(x1 - x0)
    cdef int dy = -abs(y1 - y0)
    cdef int sx = 1 if x0 < x1 else -1
    cdef int sy = 1 if y0 < y1 else -1
    cdef int err = dx + dy
    cdef int e2

    while True:
        _put_pixel(fb, width, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


cpdef void draw_lines(uint16_t[:] fb, int width, list points, uint16_t color):
    cdef int i, x0, y0, x1, y1
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        draw_line(fb, width, x0, y0, x1, y1, color)


cpdef void draw_circle(uint16_t[:] fb, int width, int cx, int cy, int radius, uint16_t color):
    cdef int x = radius
    cdef int y = 0
    cdef int err = 0

    while x >= y:
        _put_pixel(fb, width, cx + x, cy + y, color)
        _put_pixel(fb, width, cx + y, cy + x, color)
        _put_pixel(fb, width, cx - y, cy + x, color)
        _put_pixel(fb, width, cx - x, cy + y, color)
        _put_pixel(fb, width, cx - x, cy - y, color)
        _put_pixel(fb, width, cx - y, cy - x, color)
        _put_pixel(fb, width, cx + y, cy - x, color)
        _put_pixel(fb, width, cx + x, cy - y, color)
        y += 1
        if err <= 0:
            err += 2 * y + 1
        if err > 0:
            x -= 1
            err -= 2 * x + 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void draw_filled_circle(uint16_t[:] fb, int width, int cx, int cy, int radius, uint16_t color):
    cdef int x, y
    cdef int x0, x1
    cdef int r2 = radius * radius
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if (x - cx)*(x - cx) + (y - cy)*(y - cy) <= r2:
                fb[y * width + x] = color


cpdef void draw_char(
        uint16_t[:] fb,
        int width,
        int x, int y,
        char character,
        uint16_t color
):

    cdef int row, col
    cdef unsigned char bits

    cdef const unsigned char[:] glyph = font8x8_basic[character]

    for row in range(8):
        bits = glyph[row]
        for col in range(8):
            if bits & (1 << col):  # <-- remove 7 - col
                fb[(y + row) * width + (x + col)] = color


cpdef void draw_digit_48(
        uint16_t[:] fb,
        int width,
        int x, int y,
        char character,
        uint16_t color
):
    cdef int row, col
    cdef int byte_index, bit
    cdef const unsigned char[:] glyph

    # only supports '0'–'9'
    if character < ord('0') or character > ord('9'):
        return

    glyph = font48_digits[character]

    for row in range(48):
        for col in range(48):
            byte_index = row * 6 + (col >> 3)   # 6 bytes per row
            bit = 7 - (col & 7)                 # MSB first

            if glyph[byte_index] & (1 << bit):
                fb[(y + row) * width + (x + col)] = color