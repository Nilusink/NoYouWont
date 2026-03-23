"""
_memory_types.py
22.03.2026

defines structure for shared memory

Author:
Nilusink
"""
import ctypes


class road_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("ax", ctypes.c_double),
        ("ay", ctypes.c_double),
        ("bx", ctypes.c_double),
        ("by", ctypes.c_double),
        ("priority", ctypes.c_uint8),
        ("vmax", ctypes.c_uint8),
    ]


class speedcam_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("type", ctypes.c_uint8),
        ("vmax", ctypes.c_uint8),
        ("is_cluster", ctypes.c_bool),
    ]


class position_point_t(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", ctypes.c_double),
        ("y", ctypes.c_double),
        ("t", ctypes.c_double),
    ]


if __name__ == "__main__":
    print(ctypes.sizeof(road_t), ctypes.sizeof(speedcam_t))
