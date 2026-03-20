"""
_base_renderer.py
21. March 2024

prototype renderer

Author:
Nilusink
"""
import typing as tp
from ._ccolor import Color


# define types
type Color3 = tuple[float, float, float]
type Color4 = tuple[float, float, float, float]
type tColor = Color3 | Color4

# depending on the renderer, TextureID will be a different type
type TextureID = tp.Any
# type Color = tColor
type coord_t = tuple[float, float]


class BaseRenderer:
    def init(self, title: str, radius: int) -> None:
        """
        initialize the renderer and global_vars
        """
        raise NotImplementedError

    def apply_stencil[**A](
            self,
            stencil_func: tp.Callable[A, tp.Any],
            show_stencil: bool = False,
            *args: A.args,
            **kwargs: A.kwargs
    ) -> None: ...

    @staticmethod
    def start_stencil(show_stencil: bool = False) -> None: ...

    @staticmethod
    def enable_stencil(show_stencil: bool = False) -> None: ...

    def disable_stencil(self) -> None: ...

    def draw_polygon(
            self,
            vertices: tp.Iterable[coord_t],
            color: Color | tColor,
            center: coord_t = None,
            convert_global: bool = True
    ) -> None:
        raise NotImplementedError

    @staticmethod
    def check_out_of_screen(
            pos,
            size,
    ) -> bool:
        """
        check if a rect is out of screen
        """
        raise NotImplementedError

    def draw_circle(
            self,
            center: coord_t,
            radius: float,
            num_segments: int,
            color: Color | tColor,
            convert_global: bool = True
    ) -> None:
        """
        draw a circle
        """
        raise NotImplementedError

    def draw_line_circle(
            self,
            center: coord_t,
            radius: float,
            num_segments: int,
            color: Color | tColor,
            thickness: float = 1,
            convert_global: bool = True
    ):
        raise NotImplementedError

    def draw_partial_circle(
            self,
            center: coord_t,
            radius: float,
            angle_start: coord_t,
            angle_end: coord_t,
            num_segments: int,
            color: Color | tColor,
            convert_global=True
    ):
        raise NotImplementedError

    def draw_rect(
            self,
            start: coord_t,
            size: coord_t,
            color: Color | tColor,
            convert_global: bool = True
    ) -> None:
        """
        draw a rectangle
        """
        raise NotImplementedError

    def draw_dashed_circle(
            self,
            center: coord_t,
            radius: float,
            num_segments: int,
            color: Color | tColor,
            thickness: int = 1,
            convert_global: bool = True
    ) -> None:
        """
        draw a dashed circle with num_segments segments
        """
        raise NotImplementedError

    def draw_partial_dashed_circle(
            self,
            center: coord_t,
            radius: float,
            angle_start: coord_t,
            angle_end: coord_t,
            num_segments: int,
            color: Color | tColor,
            thickness=1,
            convert_global=True
    ):
        raise NotImplementedError

    def draw_line(
            self,
            vertices: tp.Iterable[coord_t],
            color: Color | tColor,
            global_position: bool = True,
            convert_global: bool = True
    ) -> None:
        """
        draw a simple line
        """
        raise NotImplementedError

    def draw_rounded_rect(
            self,
            start: coord_t,
            size: coord_t,
            color: Color | tColor,
            radius: float,
            convert_global: bool = True
            # radius_top_left: float = ...,
            # radius_top_right: float = ...,
            # radius_bottom_left: float = ...,
            # radius_bottom_right: float = ...
    ) -> None:
        """
        draw a rect with rounded corners
        """
        raise NotImplementedError

    def draw_text(
            self,
            pos: coord_t,
            text: str,
            color: Color | tColor,
            bg_color: Color | tColor,
            centered: bool = False,
            font_size: int = 64,
            font_family: str = "arial",
            bold: bool = False,
            italic: bool = False,
            convert_global: bool = True
    ) -> tuple[int, int]:
        """
        draw a text to the given position

        :returns: the size of the drawn text
        """
        raise NotImplementedError
