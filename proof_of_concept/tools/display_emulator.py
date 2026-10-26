"""
display_emulator.py
24.10.2026

Emulate the OLED display using pygame (for testing)

Author:
Nilusink
"""
# region OpenGL imports
from OpenGL.GL import glClearColor, glMatrixMode, glLoadIdentity, GL_PROJECTION
from OpenGL.GL import glEnable, GL_BLEND, glBlendFunc, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA
from OpenGL.GL import glGenTextures, glBindTexture, glTexParameteri, GL_TEXTURE_2D
from OpenGL.GL import GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_NEAREST, glDisable
from OpenGL.GL import glTexImage2D, GL_RGB, GL_UNSIGNED_SHORT_5_6_5, glTexSubImage2D
from OpenGL.GL import glBegin, glEnd, GL_QUADS, glTexCoord2f, glVertex2f, glClear, GL_COLOR_BUFFER_BIT
from OpenGL.GL import GL_STENCIL_TEST, GL_STENCIL_BUFFER_BIT, glStencilFunc, GL_ALWAYS
from OpenGL.GL import glStencilOp, GL_KEEP, GL_REPLACE, glStencilMask, GL_ALPHA_TEST
from OpenGL.GL import glAlphaFunc, GL_GREATER, glColorMask, GL_FALSE, GL_TRUE, GL_EQUAL
from OpenGL.GL import glPushMatrix, glTranslate, GL_POLYGON, glPopMatrix, glColor3f
from OpenGL.GLU import gluOrtho2D
# endregion

import pygame as pg
import numpy as np
import math as m
import mmap
import cv2


class Renderer:
    _width: int = 240
    _height: int = 240
    _bpp: int = 16  # bytes per pixel
    _device_path: str = "./disp_fb.bin"

    def __init__(self):
        # load buffer
        fb_size = self._width * self._height * (self._bpp // 8)
        self.__fb = open(self._device_path, "r+b")

        # create memory view
        self._mem = mmap.mmap(self.__fb.fileno(), fb_size)
        self._fb16 = np.frombuffer(self._mem, dtype=np.uint16)

        # img = np.frombuffer(self._fb16, dtype=np.uint16)
        # img = img.reshape(240, 240)
        # cv2.imshow("img", img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # initialize OpenGL
        pg.init()
        pg.display.gl_set_attribute(pg.GL_STENCIL_SIZE, 8)
        self._window = pg.Window(
            title="OLED Emulator",
            size=(self._width, self._height),
            opengl=True,
            resizable=False,
            hidden=False
        )

        # emulate slow re-draw speed
        self._clock = pg.Clock()

        # initialize OpenGL stuff
        glClearColor(*(0, 0, 0, 255))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self._width, self._height, 0)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # create texture ID for framebuffer
        self._texture = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self._texture)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,  # internal format
            self._width,
            self._height,
            0,
            GL_RGB,  # incoming data format
            GL_UNSIGNED_SHORT_5_6_5,  # incoming data type
            self._fb16
        )
        self.running = True

    def draw_from_buffer(self) -> None:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self._texture)

        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0, 0,
            self._width,
            self._height,
            GL_RGB,
            GL_UNSIGNED_SHORT_5_6_5,
            self._fb16
        )

        # draw quad
        glBegin(GL_QUADS)

        glTexCoord2f(0, 0)
        glVertex2f(0, 0)

        glTexCoord2f(1, 0)
        glVertex2f(self._width, 0)

        glTexCoord2f(1, 1)
        glVertex2f(self._width, self._height)

        glTexCoord2f(0, 1)
        glVertex2f(0, self._height)

        glEnd()
        glDisable(GL_TEXTURE_2D)

    def start_display_border(self) -> None:
        """
        draws the circle where the display would be
        """
        # start stencil
        glEnable(GL_STENCIL_TEST)
        glClear(GL_STENCIL_BUFFER_BIT)

        glStencilFunc(GL_ALWAYS, 1, 0xFF)
        glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
        glStencilMask(0xFF)

        glEnable(GL_ALPHA_TEST)
        glAlphaFunc(GL_GREATER, 0.01)

        glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)  # if mask invis

        # draw Stencil
        self.draw_circle(
            (self._width / 2, self._height / 2),
            min(self._width, self._height) / 2,
            64
        )

        # enable stencil
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

        glStencilMask(0x00)
        glStencilFunc(GL_EQUAL, 1, 0xFF)

    def end_display_border(self) -> None:
        """
        draws the circle where the display would be
        """
        glDisable(GL_STENCIL_TEST)
        glStencilMask(0xFF)
        glStencilFunc(GL_ALWAYS, 0, 0xFF)

    def draw_circle(
        self,
        center: tuple(int, int),
        radius: float,
        num_segments: int,
    ) -> None:
        """
        Draw a circle with fil
        :param center: Absolute center position
        :param radius: Radius of the circle in pixels
        :param num_segments: Number of segments
        :param color: Drawing color
        :param convert_global: Whether to apply the global game scaling to pos and size
        :param offscreen_check: Whether to check it the element is on the window before drawing (rect check).
        """
        glPushMatrix()
        glTranslate(center[0], center[1], 0.0)
        glColor3f(1, 1, 1)

        glBegin(GL_POLYGON)


        step = m.tau / num_segments
        [
            glVertex2f(radius * m.cos(i * step), radius * m.sin(i * step))
            for i in range(num_segments)
        ]

        glEnd()
        glPopMatrix()

    def draw_frame(self) -> None:
        self._window.flip()

        # update pygame
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

        self._clock.tick(3)

        glClear(GL_COLOR_BUFFER_BIT)
        glClearColor(.1, .1, .1, 1)  # red

    def quit(self) -> None:
        self.__fb.close()
        pg.quit()


def main() -> None:
    renderer = Renderer()

    try:
        while True:
            renderer.start_display_border()
            renderer.draw_from_buffer()
            renderer.end_display_border()

            renderer.draw_frame()

            if not renderer.running:
                break

    except KeyboardInterrupt:
        pass

    print("Closing")

    renderer.quit()

if __name__ == "__main__":
    main()