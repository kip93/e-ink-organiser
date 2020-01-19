#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)
logger.info("Loading organiser")

import httplib2
import os
from requests.exceptions import ConnectionError

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from socket import gaierror
from typing import Any, Dict, List

from modules.display.eink import Display
from modules.weather.dark_sky import Weather
from modules.calendar.google_calendar import Calendar


class Organiser:
    """Coordination class for APIs and hardware to work as an organiser."""

    _IDS = ["clear-day", "clear-night", "partly-cloudy-day", "partly-cloudy-night",
            "wind", "cloudy", "fog", "rain", "snow", "sleet"]
    """All possible weather ids."""

    def __init__(self):
        """Load modules and ready resources."""

        self._load_font()
        self._load_icons()
        self._load_modules()

    def update(self):
        """Update the organiser and refresh the display"""

        try:
            logger.debug("Updating@" + datetime.now().isoformat())
            agenda = self._calendar.list_events(50)
            forecast = self._weather.get_forecast()

            screen = Image.new("L", (300, 400), Display.WHITE)

            self._draw_forecast_bar(screen, forecast)
            self._draw_forecast_detail(screen, forecast)

            self._draw_agenda(screen, agenda)

            self._show(screen)

            logger.debug("Updated@" + datetime.now().isoformat())

        except BaseException as cause:
            logger.exception(cause)

            logger.info("Retrying update")
            self.update()

    def _load_font(self):
        """Create a font system that loads and caches resources as needed."""

        logger.info("Font by Colophon (https://fonts.google.com/specimen/Space+Mono)")

        class _Fonts:

            def __init__(self):
                self._cache = {}

            def __getitem__(self, size):
                if size not in self._cache.keys():
                    logger.debug("Loading font #{}".format(size))
                    self._cache[size] = ImageFont.truetype(os.path.join(os.path.dirname(__file__),
                                                                        "res/fonts/font.ttf"), size)

                return self._cache[size]

        self._font = _Fonts()

    def _load_icons(self):
        """Create an icon system that loads and caches resources as needed."""

        logger.info("Icons by Adam Whitcroft (http://adamwhitcroft.com/climacons/)")

        class _Icons:

            def __init__(self):
                self._cache = {}

            def __getitem__(self, name):
                if name not in self._cache.keys():
                    logger.debug("Loading icon for '{}'".format(name.replace("-", " ")))
                    self._cache[name] = Image.open(os.path.join(os.path.dirname(__file__),
                                                                "res/icons/{}.bmp".format(name)))

                return self._cache[name]

        self._icons = _Icons()

    def _load_modules(self):
        """Load modules for display, weather, and calendar."""

        logger.debug("Loading modules")

        self._display = Display()
        self._weather = Weather()

        while True:
            try:
                self._calendar = Calendar()
                break

            except (httplib2.HttpLib2Error, ConnectionError, ConnectionResetError, gaierror) as cause:
                logger.exception(cause)
                logger.info("Retrying calendar module loading")

        logger.debug("Modules loaded")

    def _draw_forecast_bar(self, image: Image, weather: Dict[str, Any]):
        """Draw the quick overview bar at the top of the screen.

        Args:
            image: the image to be drawn onto.
            weather: the forecast information to use.
        """

        canvas = ImageDraw.Draw(image)

        # Weather rectangles, coloured based on forecast
        for i in range(23):
            weather_id = weather["future"]["forecast"]["hourly"][i]["id"]
            if weather_id in ["clear-day", "clear-night", "partly-cloudy-day", "partly-cloudy-night"]:
                # NICE WEATHER
                colour = Display.WHITE

            elif weather_id in ["wind", "cloudy"]:
                # OK-ISH WEATHER
                colour = Display.LIGHT

            elif weather_id in ["fog", "rain", "snow", "sleet"]:
                # BAD WEATHER
                colour = Display.DARK

            else:
                raise ValueError("Found an unexpected weather id: {}\nDetail: {}"
                                 .format(weather_id, weather["future"]["forecast"]["hourly"][i]))

            canvas.rectangle([(i * 13, 0), ((i + 1) * 13, 8)], fill=colour)

        # Guidelines, to be able to tell to which time each rectangle corresponds
        for i in range(24):
            canvas.line([(i * 13, 8), (i * 13, 10)], fill=Display.BLACK)

            if i > 0 and i % 3 == 0:  # Scale
                text = "{:02d}".format((int(weather["now"]["time"][:2]) + i) % 24)
                canvas.text((i * 13 - 4, 11), text, font=self._font[8], fill=Display.BLACK)

        canvas.line([(0, 8), (300, 8)], fill=Display.BLACK)

    def _draw_forecast_detail(self, image: Image, weather: Dict[str, Any]):
        """Draw the detailed forecast.

        Args:
            image: the image to be drawn onto.
            weather: the forecast information to use.
        """

        canvas = ImageDraw.Draw(image)

        # Left side with main details
        icon = self._icons[weather["now"]["id"]]
        temperature = "{:d}°C".format(weather["now"]["temperature"])
        temperature_detail = "{:d}°/{:d}°".format(weather["future"]["forecast"]["daily"][0]["temperature"]["min"],
                                                  weather["future"]["forecast"]["daily"][0]["temperature"]["max"])

        description = weather["future"]["forecast"]["daily"][0]["description"] + " " + weather["future"]["summary"]

        image.paste(icon, (4, 20))
        canvas.text((55, 20), temperature, font=self._font[22], fill=Display.BLACK)
        canvas.text((55, 46), temperature_detail, font=self._font[14], fill=Display.DARK)
        canvas.text((5, 64), self._split(description, 10, 295), font=self._font[10], spacing=-1, fill=Display.BLACK)

        # Right side with extra details
        sunrise = "SR:{:s}".format(weather["future"]["forecast"]["daily"][0]["sunrise"])
        sunset = "SS:{:s}".format(weather["future"]["forecast"]["daily"][0]["sunset"])
        uv = "UV:{:s}".format(weather["now"]["uv index"])
        rain = "P:{:s}".format(weather["future"]["forecast"]["daily"][0]["precipitation"]["probability"].rjust(4))
        humidity = "H:{:s}".format(weather["now"]["humidity"].rjust(4))

        canvas.text((180, 22), sunrise, font=self._font[12], fill=Display.DARK)
        canvas.text((180, 34), sunset, font=self._font[12], fill=Display.DARK)
        canvas.text((180, 46), uv, font=self._font[12], fill=Display.DARK)
        canvas.text((250, 22), rain, font=self._font[12], fill=Display.DARK)
        canvas.text((250, 34), humidity, font=self._font[12], fill=Display.DARK)

    def _draw_agenda(self, image: Image, agenda: List[Dict[str, Any]]):
        """Draw the list of upcoming events.

        Args:
            image: the image to be drawn onto.
            agenda: the list of events to be used.
        """

        canvas = ImageDraw.Draw(image)

        last = None
        for i, event in enumerate(agenda[:21]):
            date = datetime.strptime(event["start"]["date"], "%Y-%m-%d").strftime("%d/%m")
            if date != last:
                canvas.text((5, 98 + i * 14), date, font=self._font[12], fill=Display.BLACK)
                canvas.line([(0, 100 + i * 14), (300, 100 + i * 14)], fill=Display.LIGHT)

            else:
                canvas.line([(42, 100 + i * 14), (300, 100 + i * 14)], fill=Display.LIGHT)

            colour = {"yes": Display.BLACK, "maybe": Display.BLACK, "no": Display.LIGHT, "N/A": Display.DARK}[
                event["status"]]
            if event["start"]["time"] != "N/A":
                canvas.text((44, 98 + i * 14), event["start"]["time"], font=self._font[12], fill=colour)

            canvas.text((83, 98 + i * 14), event["title"], font=self._font[12], fill=colour)

            last = date

        canvas.line([(0, 100), (300, 100)], fill=Display.DARK)
        canvas.line([(0, 394), (300, 394)], fill=Display.LIGHT)

    def _show(self, image: Image):
        """Show an image on the display.

        Args:
            image: the image to show.
        """

        self._display.wake().display(image.transpose(Image.ROTATE_90)).sleep()

    def _split(self, text: str, size: int, length: int) -> str:
        """Split a text into multiple lines if it exceeds a certain length on a given font size.

        Args:
            text: the string to be split into lines.
            size: the size of the font to be used.
            length: the maximum length, at which the string is split.

        Returns:
            A new string with new lines where needed, so that the text does not exceed the requested width.
        """

        words = text.split(" ")
        lines = []
        index = 0
        while len(words) > 0:
            index += 1
            if self._font[size].getsize(" ".join(words[:index]))[0] > length or index > len(words):
                lines.append(" ".join(words[:index - 1]))
                words = words[index - 1:]
                index = 0

        return "\n".join(lines)


if __name__ == "__main__":
    # Test the organiser

    organiser = Organiser()
    organiser.update()
