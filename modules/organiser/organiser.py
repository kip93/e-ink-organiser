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
from time import sleep
from typing import Any, Dict, List

from modules.display.eink import Display
from modules.weather.open_weather import Weather
from modules.calendar.google_calendar import Calendar


class Organiser:
    """Coordination class for APIs and hardware to work as an organiser."""

    _ICONS = ["clear-day", "clear-night", "partly-cloudy-day", "partly-cloudy-night",
              "cloudy", "fog", "rain", "snow", "thunderstorm"]
    """A list of available icons"""
    _ID_MAPPING = {
        "01d": "clear-day", "01n": "clear-night",
        "02d": "partly-cloudy-day", "02n": "partly-cloudy-night",
        "03d": "cloudy", "03n": "cloudy", "04d": "cloudy", "04n": "cloudy",
        "09d": "rain", "09n": "rain", "10d": "rain", "10n": "rain",
        "11d": "thunderstorm", "11n": "thunderstorm",
        "13d": "snow", "13n": "snow",
        "50d": "fog", "50n": "fog",
    }
    """All possible weather ids and their respective icons."""

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

            logger.info("Waiting before retry")
            sleep(300)  # Wait 5m
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
            weather_id = weather["forecast"]["hourly"][i]["id"]
            weather_icon = Organiser._ID_MAPPING.get(weather_id, None)
            if weather_icon in ["clear-day", "clear-night", "partly-cloudy-day", "partly-cloudy-night"]:
                # Nice weather
                colour = Display.WHITE

            elif weather_icon in ["cloudy"]:
                # OK-ish weather
                colour = Display.LIGHT

            elif weather_icon in ["fog", "rain", "snow", "thunderstorm"]:
                # Bad weather
                colour = Display.DARK

            else:
                raise ValueError("Found an unexpected weather id: {}\nDetail: {}"
                                 .format(weather_id, weather["forecast"]["hourly"][i]))

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
        weather_id = weather["now"]["id"]
        weather_icon = Organiser._ID_MAPPING.get(weather_id, None)
        if weather_icon is None:
            raise ValueError("Found an unexpected weather id: {}\nDetail: {}".format(weather_id, weather["now"]))

        temperature = "{:d}°C".format(weather["now"]["temperature"])
        temperature_detail = "{:d}°/{:d}°".format(weather["forecast"]["daily"][0]["temperature"]["min"],
                                                  weather["forecast"]["daily"][0]["temperature"]["max"])

        image.paste(self._icons[weather_icon], (4, 20))
        canvas.text((55, 20), temperature, font=self._font[22], fill=Display.BLACK)
        canvas.text((55, 46), temperature_detail, font=self._font[14], fill=Display.DARK)

        # Right side with extra details
        sunrise = "SR:{:s}".format(weather["forecast"]["daily"][0]["sunrise"])
        sunset = "SS:{:s}".format(weather["forecast"]["daily"][0]["sunset"])
        uv = "UV:{:s}".format(weather["now"]["uv index"])
        canvas.text((175, 22), sunrise, font=self._font[12], fill=Display.DARK)
        canvas.text((175, 34), sunset, font=self._font[12], fill=Display.DARK)
        canvas.text((175, 46), uv, font=self._font[12], fill=Display.DARK)

        pressure = "P:{:6.1f}".format(weather["now"]["pressure"])
        humidity = "H:{:s}".format(weather["now"]["humidity"])
        canvas.text((240, 22), pressure, font=self._font[12], fill=Display.DARK)
        canvas.text((240, 34), humidity, font=self._font[12], fill=Display.DARK)

    def _draw_agenda(self, image: Image, agenda: List[Dict[str, Any]]):
        """Draw the list of upcoming events.

        Args:
            image: the image to be drawn onto.
            agenda: the list of events to be used.
        """

        canvas = ImageDraw.Draw(image)

        i = 0
        y = 70
        last = None
        while i < len(agenda) and y < 400:
            start_height = y
            event = agenda[i]
            date = datetime.strptime(event["start"]["date"], "%Y-%m-%d").strftime("%d/%m")
            if date != last:
                canvas.text((5, y), date, font=self._font[12], fill=Display.BLACK)
                canvas.line([(0, y + 2), (300, y + 2)], fill=Display.DARK)

            else:
                canvas.line([(42, y + 2), (300, y + 2)], fill=Display.LIGHT)

            main_colour = {"no": Display.LIGHT, None: Display.DARK}.get(event["status"], Display.BLACK)
            extras_colour = {"no": Display.LIGHT, None: Display.LIGHT}.get(event["status"], Display.DARK)
            if event["start"]["time"] is not None:
                canvas.text((44, y), event["start"]["time"], font=self._font[12], fill=main_colour)

            title = self._split(event["title"], 12, 217)
            canvas.text((83, y), title, font=self._font[12], spacing=-4, fill=main_colour)
            y += title.count("\n") * 10

            if event["description"] is not None:
                y += 12
                description = self._split(event["description"], 12, 217)
                canvas.text((83, y), description, font=self._font[12], spacing=-4, fill=extras_colour)
                y += description.count("\n") * 10

            if event["location"] is not None:
                y += 12
                location = self._split(event["location"], 12, 217)
                canvas.text((83, y), location, font=self._font[12], spacing=-4, fill=extras_colour)
                y += location.count("\n") * 10

            i += 1
            y += 14
            last = date

            if y > 400:
                # Delete last entry if it fell off screen
                canvas.rectangle((0, start_height + 3, 300, 400), fill=Display.WHITE)

        canvas.line([(0, y + 2), (300, y + 2)], fill=Display.DARK)

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

    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    organiser = Organiser()
    organiser.update()
