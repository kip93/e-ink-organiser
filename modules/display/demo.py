#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)

import os
from typing import List

from PIL import Image


class Display:
    """Demo adapter for e-ink display."""

    SHADE: List[int] = [0x00, 0x80, 0xB0, 0xFF]  # THESE ARE DIFFERENT FROM REAL CODE DUE TO HOW IMAGES ARE SHOWN
    """A list of possible shades of grey, from black to white."""
    BLACK: int = SHADE[0]
    """A more readable name for EInk.SHADE[0]."""
    DARK: int = SHADE[1]
    """A more readable name for EInk.SHADE[1]."""
    LIGHT: int = SHADE[2]
    """A more readable name for EInk.SHADE[2]."""
    WHITE: int = SHADE[3]
    """A more readable name for EInk.SHADE[3]."""

    def __init__(self):
        """Initialise demo e-ink module."""

        self._woken = False

    def wake(self) -> "Display":
        """Activate demo e-ink module.

        Returns:
            self
        """

        self._woken = True

        return self

    def display(self, image: Image) -> "Display":
        """Save image on the screen for demo.

        Args:
            image: the image that will be saved

        Returns:
            self
        """

        if self._woken:
            if not os.path.exists(os.path.join(os.path.dirname(__file__), "res/")):
                os.makedirs(os.path.join(os.path.dirname(__file__), "res/"))

            image.transpose(Image.ROTATE_270).save(
                os.path.join(os.path.dirname(__file__), "res/demo.png"))

        return self

    def clear(self) -> "Display":
        """Clear the demo screen to white.

        Returns:
            self
        """

        if self._woken:
            if not os.path.exists(os.path.join(os.path.dirname(__file__), "res/")):
                os.makedirs(os.path.join(os.path.dirname(__file__), "res/"))

            Image.new("L", (300, 400), self.WHITE) \
                .save(os.path.join(os.path.dirname(__file__), "res/demo.png"))

        return self

    def sleep(self) -> "Display":
        """Deactivate demo e-ink module.

        Returns:
            self
        """

        self._woken = False

        return self


if __name__ == "__main__":
    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    Display().wake().clear().display(Image.new("L", (400, 300), Display.BLACK)).sleep()
