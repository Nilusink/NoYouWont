import mmap
import os
import fcntl
import struct

FBDEV = "/dev/fb1"

# Open framebuffer
fb = open(FBDEV, "r+b")

# Get screen info (resolution)
# We'll use the fixed size for simplicity; adjust as needed
WIDTH = 240
HEIGHT = 240
BPP = 16  # 16-bit 565 format

# Compute framebuffer size in bytes
fb_size = WIDTH * HEIGHT * (BPP // 8)

# mmap with the correct size
mem = mmap.mmap(fb.fileno(), fb_size)

def rgb_to_bgr565(r, g, b):
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

# Example: fill screen with red
color = 0xF800  # red in 565
color = rgb_to_bgr565(255, 255, 0)
for y in range(HEIGHT):
    for x in range(WIDTH):
        offset = (y * WIDTH + x) * 2
        mem[offset:offset+2] = color.to_bytes(2, "big")
