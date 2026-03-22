"""
_utility_functions.py
19. March 2024

a few useful functions

Author:
Nilusink
"""
import typing as tp
import pygame as pg

from ._cvectors import Vec2
from ._ccolor import Color

type coord_t = tuple[int, int] | tuple[float, float] | Vec2
type color_t = tuple[float, float, float] | tuple[float, float, float, float] | Color


ic = lambda *a, **k: print(*a, **k)


class EntityLike(tp.Protocol):
    position: Vec2
    size: Vec2
    mask: pg.Mask
    rect: pg.Rect


def classname(c: object) -> str:
    """
    get the name of an obect class
    """
    return c.__class__.__name__


def convert_coord[A: Vec2 | tuple | float](
        coord: coord_t,
        convert_to: type[A] = tuple
) -> A | tuple[float, float] | tuple[A, A]:
    """
    accepts both tuple and Vec2
    """
    if convert_to is Vec2:
        if isinstance(coord, Vec2):
            return coord.copy()

        return Vec2().from_cartesian(*coord)

    if convert_to is tuple:
        if isinstance(coord, tuple):
            return coord

        return coord.xy

    if convert_to is int:
        if isinstance(coord, Vec2):
            coord = coord.xy

        return int(coord[0]), int(coord[1])

    raise ValueError("Unsupported conversion: ", convert_to)


def convert_color[A: Color | int | float](
        color: color_t,
        convert_to: type[A] = tuple
) -> A | tuple[A, A, A, A]:
    if convert_to is Color:
        if isinstance(color, Color):
            return color.copy()

        if max(color) > 1:
            return Color().from_255(*color)

        return Color().from_1(*color)

    elif convert_to is int:
        if isinstance(color, Color):
            return color.get_rgba255()

        else:
            # noinspection PyTypeChecker
            return *(round(c * 255) for c in color),

    else:
        if isinstance(color, Color):
            return color.get_rgba1()
        # noinspection PyTypeChecker
        return *(c / 255 for c in color),
