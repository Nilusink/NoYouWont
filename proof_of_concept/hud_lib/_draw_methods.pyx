# cython: boundscheck=False, wraparound=False, cdivision=True
cimport cython
from libc.math cimport sqrt
from libc.stdint cimport uint16_t
from ._cfonts cimport font8x8_basic, font48_bahnschrift, font96_bahnschrift


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void _put_pixel(uint16_t[:] fb, int width, int x, int y, uint16_t color):
    fb[y * width + x] = color


@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline void _draw_span(
        uint16_t[:] fb,
        int row,
        int x0, int x1,
        int width,
        uint16_t color
):
    if x0 > x1:
        x0, x1 = x1, x0

    if x1 < 0 or x0 >= width:
        return

    if x0 < 0:
        x0 = 0
    if x1 >= width:
        x1 = width - 1

    cdef int x
    for x in range(x0, x1 + 1):
        fb[row + x] = color


@cython.boundscheck(False)
@cython.wraparound(False)
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


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void draw_lines(uint16_t[:] fb, int width, list points, uint16_t color):
    cdef int i, x0, y0, x1, y1
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        draw_line(fb, width, x0, y0, x1, y1, color)


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void draw_circle(
        uint16_t[:] fb,
        int width, int height,
        int cx, int cy,
        int radius,
        int thickness,
        uint16_t color
):
    cdef int y
    cdef int outer_r = radius
    cdef int inner_r = radius - thickness

    if inner_r < 0:
        inner_r = 0

    cdef int outer_x, inner_x
    cdef int dy
    cdef int row

    for dy in range(-outer_r, outer_r + 1):
        y = cy + dy
        if y < 0 or y >= height:
            continue

        # compute x extents using circle equation
        outer_x = <int>sqrt(outer_r * outer_r - dy * dy)

        if abs(dy) <= inner_r:
            inner_x = <int>sqrt(inner_r * inner_r - dy * dy)
        else:
            inner_x = 0

        row = y * width

        # ---- left span ----
        _draw_span(fb, row, cx - outer_x, cx - inner_x, width, color)

        # ---- right span ----
        _draw_span(fb, row, cx + inner_x, cx + outer_x, width, color)

cpdef void draw_rect(
        uint16_t[:] fb,
        int width,
        int height,
        int x, int y,
        int w, int h,
        uint16_t color
):
    if w <= 0 or h <= 0:
        return

    cdef int x0 = x
    cdef int y0 = y
    cdef int x1 = x + w - 1
    cdef int y1 = y + h - 1

    # Clip vertically
    if y1 < 0 or y0 >= height:
        return

    if y0 < 0:
        y0 = 0
    if y1 >= height:
        y1 = height - 1

    cdef int row, py
    for py in range(y0, y1 + 1):
        row = py * width
        _draw_span(fb, row, x0, x1, width, color)


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


cpdef void draw_char_48(
        uint16_t[:] fb,
        int width,
        int x, int y,
        char character,
        uint16_t color
):
    cdef const unsigned char[:] glyph = font48_bahnschrift[character]

    cdef int row, col_byte, bit
    cdef unsigned char b
    cdef int base_index
    cdef int px

    for row in range(48):
        base_index = row * 6  # 48 bits = 6 bytes

        for col_byte in range(6):
            b = glyph[base_index + col_byte]

            if b == 0:
                continue  # skip empty block

            px = x + col_byte * 8

            # unrolled bit loop (faster than range)
            if b & 0x80: fb[(y+row)*width + px+0] = color
            if b & 0x40: fb[(y+row)*width + px+1] = color
            if b & 0x20: fb[(y+row)*width + px+2] = color
            if b & 0x10: fb[(y+row)*width + px+3] = color
            if b & 0x08: fb[(y+row)*width + px+4] = color
            if b & 0x04: fb[(y+row)*width + px+5] = color
            if b & 0x02: fb[(y+row)*width + px+6] = color
            if b & 0x01: fb[(y+row)*width + px+7] = color


cpdef void draw_char_96(
        uint16_t[:] fb,
        int width,
        int x, int y,
        char character,
        uint16_t color
):
    cdef const unsigned char[:] glyph = font96_bahnschrift[character]

    cdef int row, col_byte
    cdef unsigned char b
    cdef int base_index
    cdef int px
    cdef int fb_row

    for row in range(96):
        base_index = row * 12  # 96 bits = 12 bytes
        fb_row = (y + row) * width

        for col_byte in range(12):
            b = glyph[base_index + col_byte]

            if b == 0:
                continue

            px = x + col_byte * 8

            # fully unrolled (same as 48x48)
            if b & 0x80: fb[fb_row + px + 0] = color
            if b & 0x40: fb[fb_row + px + 1] = color
            if b & 0x20: fb[fb_row + px + 2] = color
            if b & 0x10: fb[fb_row + px + 3] = color
            if b & 0x08: fb[fb_row + px + 4] = color
            if b & 0x04: fb[fb_row + px + 5] = color
            if b & 0x02: fb[fb_row + px + 6] = color
            if b & 0x01: fb[fb_row + px + 7] = color
