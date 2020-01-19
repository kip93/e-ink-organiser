#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)
logger.info("Display by Waveshare Electronics (https://www.waveshare.com/wiki/4.2inch_e-Paper_Module)")

import os
import time
from typing import List, Tuple, Union

import numpy
from PIL import Image
import RPi.GPIO
import spidev


class Display:
    """Adapter for Waveshare 4.2" e-ink display using a RPi."""

    _WIDTH, _HEIGHT = 400, 300
    """The size of the e-ink display."""

    SHADE: List[int] = [0x00, 0x40, 0x80, 0xC0]
    """A list of possible shades of gray, from black to white."""
    BLACK: int = SHADE[0]
    """A more readable name for Display.SHADE[0]."""
    DARK: int = SHADE[1]
    """A more readable name for Display.SHADE[1]."""
    LIGHT: int = SHADE[2]
    """A more readable name for Display.SHADE[2]."""
    WHITE: int = SHADE[3]
    """A more readable name for Display.SHADE[3]."""

    _ENABLE: int = 8
    """GPIO pin for CS (Chip Select) line, used to enable SPI communication."""
    _RESET: int = 17
    """GPIO pin for RST (Hardware reset) line, used to reset the device."""
    _BUSY: int = 24
    """GPIO pin for BUSY line, used to wait until all pending operations have been completed."""
    _MODE: int = 25
    """GPIO pin for DC (Data Command) line, used to distinguish between data and commands."""
    _LED: int = 27
    """GPIO pin for the status LED, used to notify if there is any ongoing communication."""

    _EMPTY: numpy.ndarray = numpy.full(_WIDTH * _HEIGHT // 8, WHITE, dtype=numpy.uint8)
    """An empty screen, used during screen clearing."""

    def __init__(self):
        """Initialise RPi to communicate with e-ink module."""

        self._gpio = RPi.GPIO  # Initialise RPi GPIO pins
        self._gpio.setmode(self._gpio.BCM)  # Use BCM numbering system
        self._gpio.setwarnings(False)
        self._gpio.setup(Display._ENABLE, self._gpio.OUT)
        self._gpio.setup(Display._RESET, self._gpio.OUT)
        self._gpio.setup(Display._BUSY, self._gpio.IN)
        self._gpio.setup(Display._MODE, self._gpio.OUT)
        self._gpio.setup(Display._LED, self._gpio.OUT)
        self._gpio.output(Display._LED, 1)

        self._spi = spidev.SpiDev(0, 0)  # RPi SPI0
        self._spi.max_speed_hz = 4000000  # 4MHz
        self._spi.mode = 0b00

    def __del__(self):
        """Close the RPi communication with the e-ink module."""

        self._spi.close()

        self._gpio.output(Display._RESET, 0)
        self._gpio.output(Display._MODE, 0)
        self._gpio.output(Display._LED, 0)
        self._gpio.cleanup()

    def wake(self) -> "Display":
        """Activate e-ink module.

        Returns:
            self
        """

        logger.debug("Wake up")

        self._reset()
        self._send(0x01, [0x03, 0x00, 0x2B, 0x2B, 0x13])  # Power Settings
        self._send(0x06, [0x17, 0x17, 0x17])  # Booster Soft Start
        self._send(0x04, [])  # Power ON
        self._send(0x00, [0x3F])  # Panel Settings
        self._send(0x30, [0x3C])  # PLL Settings
        self._send(0x61, [0x01, 0x90, 0x01, 0x2C])  # Resolution Settings
        self._send(0x82, [0x12])  # Common voltage DC Settings
        self._send(0x50, [0x97])  # Common voltage and Data Interval Settings

        self._init_lut()

        logger.debug("Waked up")

        return self

    def display(self, image: Image) -> "Display":
        """Show an image on the screen.

        This assumes that the module has been activated, and that the image is a
        horizontal B&W bmp image of the same size as the display resolution.

        Args:
            image: the image that will be shown

        Returns:
            self
        """

        logger.debug("Update")

        if image is None:
            raise TypeError("The image cannot be None")

        buffer = self._get_buffer(image)
        size = self._WIDTH * self._HEIGHT // 8
        data1, data2 = numpy.empty(size, dtype=numpy.uint8), numpy.empty(size, dtype=numpy.uint8)
        for i in range(size):
            byte1, byte2 = 0, 0
            for j in range(2):
                chunk = buffer[i * 2 + j]
                for k in range(2):
                    masks = self._get_masks(chunk)
                    byte1 |= masks[0]
                    byte2 |= masks[1]

                    byte1 <<= 1
                    byte2 <<= 1
                    chunk <<= 2

                    masks = self._get_masks(chunk)
                    byte1 |= masks[0]
                    byte2 |= masks[1]

                    if j != 1 or k != 1:
                        byte1 <<= 1
                        byte2 <<= 1

                    chunk <<= 2

            data1[i] = byte1
            data2[i] = byte2

        self._send(0x10, data1)
        self._send(0x13, data2)
        self._send(0x12, [])

        logger.debug("Updated")

        return self

    def clear(self) -> "Display":
        """Clear the screen to white.

        Returns:
            self
        """

        logger.debug("Clear")

        self._send(0x10, Display._EMPTY)
        self._send(0x13, Display._EMPTY)
        self._send(0x12, [])

        logger.debug("Cleared")

        return self

    def sleep(self) -> "Display":
        """Deactivate e-ink module, putting it in deep sleep (Low power mode).

        Returns:
            self
        """

        logger.debug("Sleep")

        self._send(0x02, [])  # Power OFF
        self._send(0x07, [0xA5])  # Deep Sleep

        logger.debug("Slept")

        return self

    def _reset(self):
        """Do a hardware reset of the e-ink module."""

        logger.debug("Reset")

        self._gpio.output(Display._RESET, 1)
        time.sleep(.2)
        self._gpio.output(Display._RESET, 0)
        time.sleep(.2)
        self._gpio.output(Display._RESET, 1)
        time.sleep(.2)

        logger.debug("Reset")

    def _init_lut(self):
        """Initialise the e-ink module's look up tables (LUT).

        These will define how the display shows data.
        """

        logger.debug("Initialise LUT")

        self._send(0x20, [0x00, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x60, 0x14,
                          0x14, 0x00, 0x00, 0x01, 0x00, 0x14, 0x00, 0x00,
                          0x00, 0x01, 0x00, 0x13, 0x0A, 0x01, 0x00, 0x01,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00])  # COMMON VOLTAGE LUT

        self._send(0x21, [0x40, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x90, 0x14,
                          0x14, 0x00, 0x00, 0x01, 0x10, 0x14, 0x0A, 0x00,
                          0x00, 0x01, 0xA0, 0x13, 0x01, 0x00, 0x00, 0x01,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00])  # WHITE TO WHITE LUT

        self._send(0x22, [0x40, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x90, 0x14,
                          0x14, 0x00, 0x00, 0x01, 0x00, 0x14, 0x0A, 0x00,
                          0x00, 0x01, 0x99, 0x0C, 0x01, 0x03, 0x04, 0x01,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00])  # BLACK TO WHITE LUT

        self._send(0x23, [0x40, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x90, 0x14,
                          0x14, 0x00, 0x00, 0x01, 0x00, 0x14, 0x0A, 0x00,
                          0x00, 0x01, 0x99, 0x0B, 0x04, 0x04, 0x01, 0x01,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00])  # WHITE TO BLACK LUT

        self._send(0x24, [0x80, 0x0A, 0x00, 0x00, 0x00, 0x01, 0x90, 0x14,
                          0x14, 0x00, 0x00, 0x01, 0x20, 0x14, 0x0A, 0x00,
                          0x00, 0x01, 0x50, 0x13, 0x01, 0x00, 0x00, 0x01,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00])  # BLACK TO BLACK LUT

        logger.debug("LUT initialised")

    def _send(self, command: int, data: Union[List[int], numpy.ndarray]):
        """Send a command to the e-ink module

        Args:
            command: the id of the command to be sent
            data: a list of values to be sent along the command
        """

        logger.debug("Send 0x{:02X} command with [{}] as data"
                     .format(command, ", ".join("0x{:02X}".format(byte) for byte in data)))

        self._gpio.output(Display._MODE, 0)  # Command mode
        self._gpio.output(Display._ENABLE, 0)  # Enable communication
        self._spi.writebytes([command])

        self._gpio.output(Display._MODE, 1)  # Data mode
        for byte in data:
            self._spi.writebytes([int(byte)])

        self._gpio.output(Display._ENABLE, 1)  # Finish communication

        self._wait()

        logger.debug("Command and data sent")

    def _wait(self):
        """Wait until the e-ink is done processing.

        This will also blink the LED to indicate that module is waiting.
        """

        logger.debug("Waiting")

        self._gpio.output(Display._LED, 0)  # Turn OFF LED
        time.sleep(50e-3)  # 50 ms

        state = 0
        while self._gpio.input(Display._BUSY) == 0:
            state ^= 1
            self._gpio.output(Display._LED, state)  # Blink LED
            time.sleep(50e-3)  # 50 ms

        self._gpio.output(Display._LED, 1)  # Turn ON LED
        time.sleep(50e-3)  # 50 ms

        logger.debug("Waited")

    @staticmethod
    def _get_buffer(image: Image) -> numpy.ndarray:
        """Get an array with the data in the image as 2 bit B&W values.

        Args:
            image: a monochrome image to be converted.

        Returns:
            A buffer with the transformed data.
        """

        buffer = numpy.empty(Display._WIDTH * Display._HEIGHT // 4, dtype=numpy.uint8)
        for j in range(Display._HEIGHT):
            for i in range(0, Display._WIDTH, 4):
                buffer[(i + j * Display._WIDTH) // 4] = ((image.getpixel((i - 3, j)) & 0xC0) >> 0 |
                                                         (image.getpixel((i - 2, j)) & 0xC0) >> 2 |
                                                         (image.getpixel((i - 1, j)) & 0xC0) >> 4 |
                                                         (image.getpixel((i - 0, j)) & 0xC0) >> 6)

        return buffer

    @staticmethod
    def _get_masks(data: int) -> Tuple[int, int]:
        """Get the masks to be applied during the processing of an image to be shown.

        Args:
            data: the integer to analyse.

        Returns:
            Two masks to be applied to on each phase of the image displaying
        """

        masked = data & 0xC0
        if masked == 0xC0:  # WHITE
            return 0x01, 0x01

        elif masked == 0x80:  # LIGHT
            return 0x01, 0x00

        elif masked == 0x40:  # DARK
            return 0x00, 0x01

        elif masked == 0x00:  # BLACK
            return 0x00, 0x00


# Check that GPIO drivers are reachable
if not os.path.exists("/sys/bus/platform/drivers/gpiomem-bcm2835"):
    raise RuntimeError("GPIO drivers not found")

if __name__ == "__main__":
    # Test the display module

    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    Display().wake().clear().display(Image.new("L", (400, 300), Display.BLACK)).sleep()
