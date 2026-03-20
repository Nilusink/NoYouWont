"""
_opengl.py
21. March 2024

a few functions for rendering

Author:
Nilusink
"""
from OpenGL.GL import glTranslate, glMatrixMode, glLoadIdentity, glTexCoord2f
from OpenGL.GL import GL_PROJECTION, GL_SRC_ALPHA, GL_BLEND, GL_CLAMP_TO_EDGE
from OpenGL.GL import glBindTexture, glTexParameteri, glTexImage2D, glEnable
from OpenGL.GL import glGenTextures, glVertex2f, glColor3f, glColor4f, glEnd
from OpenGL.GL import GL_UNSIGNED_BYTE, GL_MODELVIEW, GL_ONE_MINUS_SRC_ALPHA
from OpenGL.GL import GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT, GL_LINES
from OpenGL.GL import GL_TEXTURE_WRAP_T, GL_TEXTURE_MIN_FILTER, GL_POLYGON
from OpenGL.GL import glDisable, glBegin, glVertex, glFlush, glClearColor
from OpenGL.GL import glBlendFunc, glWindowPos2d, glDrawPixels, glRotated
from OpenGL.GL import glPopMatrix, glPushMatrix
from OpenGL.GL import glTranslated, GL_TRIANGLE_STRIP, glStencilFunc, GL_KEEP
from OpenGL.GL import glStencilOp, glStencilMask, GL_STENCIL_TEST, GL_ALWAYS
from OpenGL.GL import GL_REPLACE, GL_EQUAL, glClear, GL_STENCIL_BUFFER_BIT
from OpenGL.GL import glGetIntegerv, GL_STENCIL_BITS, GL_ALPHA_TEST, GL_FALSE
from OpenGL.GL import glAlphaFunc, GL_GREATER, glColorMask, GL_TRUE
from OpenGL.GLU import gluOrtho2D
from pygame.locals import DOUBLEBUF, OPENGL
import pygame as pg
import typing as tp
import math as m

from ._base_renderer import BaseRenderer, tColor
from ._cvectors import Vec2, normalize_angle
from ._ccolor import Color
from ._utility_functions import convert_coord

def ic(*args, **kwargs):
    print(*args, **kwargs)

# define types
type TextureID = int


class OpenGLRenderer(BaseRenderer):
    def check_out_of_screen(self, *_, **__):
        pass

    def get_font(
            self,
            size: int,
            family: str,
            bold: bool = False,
            italic: bool = False
    ) -> pg.font.Font:
        # check if font exists
        if size in self._fonts:
            for font in self._fonts[size]:  # TODO: fix
                if all([
                    font.name == family,
                    font.bold == bold,
                    font.italic == italic
                ]):
                    return font

        else:
            self._fonts[size] = []

        # no font found, create new
        new_font = pg.font.SysFont(family, int(size), bold, italic)
        self._fonts[size].append(new_font)

        return new_font

    def init(self, title, radius):
        ic("using OpenGL backend")

        pg.font.init()

        self._fonts = {
            32: [
                pg.font.SysFont('arial', 32)
            ],
            64: [
                pg.font.SysFont('arial', 64)
            ]
        }

        # get screen size
        # screen_info = pg.display.Info()
        window_size = 2*(radius*2,)  # (screen_info.current_w, screen_info.current_h)  # TODO: sizing
        # window_size = 1920, 1080

        # set global screen size and ppm

        pg.display.gl_set_attribute(pg.GL_STENCIL_SIZE, 8)
        pg.display.set_mode(
            window_size,
            DOUBLEBUF | OPENGL
        )
        # self.font = pg.font.SysFont(None, 24)
        # request stencil buffer
        pg.display.set_caption(title)

        # initialize OpenGL stuff
        glClearColor(*(0, 0, 0, 1))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, *window_size, 0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    @staticmethod
    def set_color(color: Color | tColor) -> Color:
        """
        set gColor
        """
        # color as Color class
        if isinstance(color, Color):

            glColor4f(*color.rgba1)

            return color

        # color as tuple
        else:
            if len(color) == 3:
                glColor3f(*color)

            elif len(color) == 4:
                glColor4f(*color)

            else:
                raise ValueError("Invalid color: ", color)

            return Color().from_1(*color)

    def apply_stencil[**A](
            self,
            stencil_func: tp.Callable[A, tp.Any],
            show_stencil=False,
            *args: A.args,
            **kwargs: A.kwargs
    ) -> None:
        self.start_stencil(show_stencil)

        stencil_func(*args, **kwargs)

        self.enable_stencil(show_stencil)

    @staticmethod
    def start_stencil(show_stencil=False):
        """
        call this, then draw stencil, then draw enable_stencil
        """
        glEnable(GL_STENCIL_TEST)
        glClear(GL_STENCIL_BUFFER_BIT)

        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
        glStencilMask(0xFF)

        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GREATER, 0.01)

        if not show_stencil:
            glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)  # if mask invis

    @staticmethod
    def enable_stencil(show_stencil=False):
        """
        start_stencil must be called first
        """
        if not show_stencil:
            glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

        glStencilMask(0x00)
        glStencilFunc(GL_EQUAL, 1, 0xFF)

    def disable_stencil(self) -> None:
        glDisable(GL_STENCIL_TEST)
        glStencilMask(0xFF)
        glStencilFunc(GL_ALWAYS, 0, 0xFF)

    def draw_polygon(
            self,
            vertices,
            color,
            center=None,
            convert_global=True
    ):
        vertices = [convert_coord(v, Vec2) for v in vertices]

        glPushMatrix()
        if center is not None:
            center = convert_coord(center, Vec2)
            glTranslate(center.x, center.y, 0)

        self.set_color(color)

        glBegin(GL_POLYGON)

        for vertice in vertices:
            glVertex2f(*vertice.xy)

        glEnd()
        glPopMatrix()

    def draw_circle(
            self,
            center,
            radius,
            num_segments,
            color,
            convert_global=True,
    ):
        center = convert_coord(center, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(center, (radius, 0)):
            return

        glPushMatrix()
        glTranslate(center.x, center.y, 0)

        self.set_color(color)

        glBegin(GL_POLYGON)

        for i in range(num_segments):
            cosine = radius * m.cos(i * 2 * m.pi / num_segments)
            sine = radius * m.sin(i * 2 * m.pi / num_segments)
            glVertex2f(cosine, sine)

        glEnd()
        glPopMatrix()

    def draw_line_circle(
            self,
            center,
            radius,
            num_segments,
            color,
            thickness=1,
            convert_global=True,
    ):
        center = convert_coord(center, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(center, (radius, 0)):
            return

        glPushMatrix()  # reset previous glTranslate statements
        glTranslate(center.x, center.y, 0)

        self.set_color(color)

        glBegin(GL_TRIANGLE_STRIP)

        inner = radius
        outer = radius + thickness

        angle_step = 2 * m.pi / num_segments
        for i in range(num_segments + 1):
            angle = i * angle_step
            c = m.cos(angle)
            s = m.sin(angle)

            glVertex2f(outer * c, outer * s)
            glVertex2f(inner * c, inner * s)

        glEnd()
        glPopMatrix()

    def draw_partial_circle(
            self,
            center,
            radius,
            angle_start,
            angle_end,
            num_segments,
            color,
            convert_global=True
    ):
        center = convert_coord(center, Vec2)
        angle_start = convert_coord(angle_start, Vec2)
        angle_end = convert_coord(angle_end, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(center, (radius, 0)):
            return

        angle_delta = (
                normalize_angle(angle_end.angle)
                - normalize_angle(angle_start.angle)
        )

        glPushMatrix()
        glTranslate(center.x, center.y, 0)

        self.set_color(color)

        glBegin(GL_POLYGON)
        glVertex2f(0, 0)

        for i in range(num_segments + 1):
            angle = angle_start.angle + (i / num_segments) * angle_delta
            pos = Vec2().from_polar(
                angle,
                radius
            )
            glVertex2f(*pos.xy)

        glEnd()
        glPopMatrix()

    def draw_rect(
            self,
            start,
            size,
            color,
            convert_global=True
    ):
        start = convert_coord(start, Vec2)
        size = convert_coord(size, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(start, size):
            return

        glPushMatrix()
        glTranslate(start.x, start.y, 0)

        self.set_color(color)

        glBegin(GL_POLYGON)
        glVertex2f(0, 0)
        glVertex2f(size.x, 0)
        glVertex2f(size.x, size.y)
        glVertex2f(0, size.y)
        glEnd()
        glPopMatrix()

    def draw_dashed_circle(
            self,
            center,
            radius,
            num_segments,
            color,
            thickness=1,
            convert_global=True
    ):
        center = convert_coord(center, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(center, (radius + thickness, 0)):
            return

        glPushMatrix()
        glTranslate(center.x, center.y, 0)

        self.set_color(color)

        for i in range(num_segments):
            i1 = i * 2
            i2 = i1 + 1

            cosine1 = m.cos(i1 * 2 * m.pi / num_segments)
            sine1 = m.sin(i1 * 2 * m.pi / num_segments)

            cosine2 = m.cos(i2 * 2 * m.pi / num_segments)
            sine2 = m.sin(i2 * 2 * m.pi / num_segments)

            glBegin(GL_POLYGON)
            glVertex2f(cosine1 * radius, sine1 * radius)
            glVertex2f(
                cosine1 * (radius + thickness),
                sine1 * (radius + thickness)
            )
            glVertex2f(
                cosine2 * (radius + thickness),
                sine2 * (radius + thickness)
            )
            glVertex2f(cosine2 * radius, sine2 * radius)
            glEnd()

        glPopMatrix()

    def draw_partial_dashed_circle(
            self,
            center,
            radius,
            angle_start,
            angle_end,
            num_segments,
            color,
            thickness=1,
            convert_global=True
    ):
        center = convert_coord(center, Vec2)
        angle_start = convert_coord(angle_start, Vec2)
        angle_end = convert_coord(angle_end, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(center, (radius + thickness, 0)):
            return

        angle_delta = normalize_angle(
            angle_end.angle - angle_start.angle
        ) / 2

        glPushMatrix()
        glTranslate(center.x, center.y, 0)

        self.set_color(color)

        for i in range(num_segments):
            i1 = i * 2
            i2 = i1 + 1

            angle1 = angle_start.angle + (i1 / num_segments) * angle_delta
            angle2 = angle_start.angle + (i2 / num_segments) * angle_delta

            pos1 = Vec2().from_polar(
                angle1,
                1
            )
            pos2 = Vec2().from_polar(
                angle2,
                1
            )

            glBegin(GL_POLYGON)
            glVertex2f(*(pos1 * radius).xy)
            glVertex2f(*(pos1 * (radius + thickness)).xy)
            glVertex2f(*(pos2 * (radius + thickness)).xy)
            glVertex2f(*(pos2 * radius).xy)
            glEnd()

        glPopMatrix()

    def draw_line(
            self,
            vertices,
            color,
            global_position=True,
            convert_global=True
    ):
        """
        draw a simple line
        """
        # vertices = [convert_coord(v, tuple) for v in vertices]

        # only draw if on screen

        if global_position:
            glPushMatrix()  # reset previous glTranslate statements

        self.set_color(color)

        glBegin(GL_LINES)

        for vertice in vertices:
            glVertex2f(*vertice)

        glEnd()
        glPopMatrix()

    def draw_rounded_rect(
            self,
            start,
            size,
            color,
            radius,
            convert_global=True
    ) -> None:
        start = convert_coord(start, Vec2)
        size = convert_coord(size, Vec2)

        # only draw if on screen
        if OpenGLRenderer.check_out_of_screen(start, size):
            return

        # circles at edges
        self.draw_circle(
            start + radius,
            radius,
            m.ceil(radius),
            color,
            convert_global
        )
        self.draw_circle(
            start + size - radius,
            radius,
            m.ceil(radius),
            color,
            convert_global
        )
        self.draw_circle(
            (
                start.x + size.x - radius,
                start.y + radius
            ),
            radius,
            m.ceil(radius),
            color,
            convert_global
        )
        self.draw_circle(
            (
                start.x + radius,
                start.y + size.y - radius
            ),
            radius,
            m.ceil(radius),
            color,
            convert_global
        )

        # fill in squares
        if size.x > 2 * radius:
            self.draw_rect(
                (
                    start.x + radius,
                    start.y
                ),
                (
                    size.x - 2 * radius,
                    size.y
                ),
                color,
                convert_global
            )

        if size.y > 2 * radius:
            self.draw_rect(
                (
                    start.x,
                    start.y + radius
                ),
                (
                    size.x,
                    size.y - 2 * radius
                ),
                color,
                convert_global
            )
