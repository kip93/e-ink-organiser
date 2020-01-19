#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)
logger.info("Weather powered by Dark Sky (https://darksky.net/poweredby/)")

from datetime import datetime
import json
import os
import pytz
import requests
from typing import Any, Dict


class Weather:
    """Dark Sky weather API wrapper."""

    _HEADERS = {"Accept-Encoding": "gzip"}
    """Headers for the requests to be sent."""

    _PARAMETERS = {"lang": "en", "units": "si", "extend": "hourly", "exclude": "[minutely,alerts,flags]"}
    """Query parameters for weather API."""

    _COMPASS_ROSE = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    """A compass rose used to define which direction the wind is blowing from."""

    def __init__(self):
        """Load configuration from file and initialise."""

        with open(os.path.join(os.path.dirname(__file__), "res/credentials.json"), "r") as file:
            credentials = json.load(file)

        with open(os.path.join(os.path.dirname(__file__), "res/configuration.json"), "r") as file:
            configuration = json.load(file)

        api_key = credentials["api_key"]
        latitude, longitude = configuration["latitude"], configuration["longitude"]

        self._url = "https://api.darksky.net/forecast/{}/{},{}".format(api_key, latitude, longitude)

    def get_forecast(self) -> Dict[str, Any]:
        """Get the forecast from the weather API and normalise it.

        Returns:
            A dictionary with the information of current and upcoming weather.
        """

        logger.debug("Fetching forecast")

        try:
            response = requests.get(self._url, headers=self._HEADERS, params=self._PARAMETERS, timeout=(10, 10))

            if response.status_code == 200:
                logger.debug("Forecast fetched")

                return self._normalise_data(response.json())

            else:
                raise ResourceWarning("{} {}\nDetail: {}"
                                      .format(response.status_code, response.reason, response.json()))

        except requests.exceptions.Timeout:
            raise TimeoutError("Timeout while getting weather data")

    @staticmethod
    def _normalise_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform the json data of the weather API into a normalised format.

        Args:
            data: the API's output.

        Returns:
            The new dictionary with the normalised information.
        """

        return {
            "now": {
                "date": Weather._get_date(data["currently"]["time"], data["timezone"]),
                "time": Weather._get_time(data["currently"]["time"], data["timezone"]),
                "description": data["currently"]["summary"],
                "id": data["currently"]["icon"],

                "temperature": round(data["currently"]["temperature"]),
                "feels like": round(data["currently"]["apparentTemperature"]),

                "clouds": Weather._get_percentage(data["currently"].get("cloudCover", 0)),
                "pressure": data["currently"].get("pressure", "N/A"),
                "wind": {
                    "speed": round(data["currently"].get("windSpeed", 0)),
                    "direction": Weather._get_direction(data["currently"].get("windBearing", None)),
                },

                "humidity": Weather._get_percentage(data["currently"].get("humidity", 0)),
                "precipitation": {
                    "probability": Weather._get_percentage(data["currently"].get("precipProbability", 0)),
                    "intensity": data["currently"].get("precipIntensity", 0),
                },

                "uv index": Weather._get_uv_index(data["currently"]["uvIndex"]),
            },
            "future": {
                "summary": data["daily"]["summary"],
                "forecast": {
                    "daily": [
                        {
                            "date": Weather._get_date(data["daily"]["data"][i]["time"], data["timezone"]),
                            "description": data["daily"]["data"][i]["summary"],
                            "id": data["daily"]["data"][i]["icon"],

                            "temperature": {
                                "min": round(data["daily"]["data"][i]["temperatureLow"]),
                                "max": round(data["daily"]["data"][i]["temperatureHigh"]),
                            },

                            "clouds": Weather._get_percentage(data["daily"]["data"][i].get("cloudCover", 0)),
                            "pressure": data["daily"]["data"][i].get("pressure", "N/A"),
                            "wind": {
                                "speed": round(data["daily"]["data"][i].get("windSpeed", 0)),
                                "direction": Weather._get_direction(data["daily"]["data"][i].get("windBearing", None)),
                            },

                            "humidity": Weather._get_percentage(data["daily"]["data"][i].get("humidity", 0)),
                            "precipitation": {
                                "probability":
                                    Weather._get_percentage(data["daily"]["data"][i].get("precipProbability", 0)),
                                "intensity": data["daily"]["data"][i].get("precipIntensity", 0),
                            },

                            "uv index": Weather._get_uv_index(data["daily"]["data"][i]["uvIndex"]),
                            "sunrise": Weather._get_time(data["daily"]["data"][i]["sunriseTime"], data["timezone"]),
                            "sunset": Weather._get_time(data["daily"]["data"][i]["sunsetTime"], data["timezone"]),

                        } for i in range(len(data["daily"]["data"]))
                    ],
                    "hourly": [
                        {
                            "date": Weather._get_date(data["hourly"]["data"][i]["time"], data["timezone"]),
                            "time": Weather._get_time(data["hourly"]["data"][i]["time"], data["timezone"]),
                            "description": data["hourly"]["data"][i]["summary"],
                            "id": data["hourly"]["data"][i]["icon"],

                            "temperature": round(data["hourly"]["data"][i]["temperature"]),

                            "clouds": Weather._get_percentage(data["hourly"]["data"][i].get("cloudCover", 0)),
                            "pressure": data["hourly"]["data"][i].get("pressure", "N/A"),
                            "wind": {
                                "speed": round(data["hourly"]["data"][i].get("windSpeed", 0)),
                                "direction": Weather._get_direction(data["hourly"]["data"][i].get("windBearing", None)),
                            },

                            "humidity": Weather._get_percentage(data["hourly"]["data"][i].get("humidity", 0)),
                            "precipitation": {
                                "probability":
                                    Weather._get_percentage(data["hourly"]["data"][i].get("precipProbability", 0)),
                                "intensity": data["hourly"]["data"][i].get("precipIntensity", 0),
                            },

                            "uv index": Weather._get_uv_index(data["hourly"]["data"][i]["uvIndex"]),

                        } for i in range(len(data["hourly"]["data"]))
                    ]
                },
            },
        }

    @staticmethod
    def _get_direction(degrees: float) -> str:
        """Get the cardinal direction from where the wind is blowing.

        Args:
            degrees: the angle at which the wind is blowing from, with the north as zero, and increasing clock-wise.

        Returns:
            A string for the abbreviation of the direction.
        """

        if degrees is None:
            return "N/A"

        else:
            return Weather._COMPASS_ROSE[round((degrees % 360) / 22.5)]

    @staticmethod
    def _get_uv_index(index: int) -> str:
        """Get a human readable name for the given UV index.

        Args:
            index: the index value being transformed.

        Returns:
            A string with the severity of the UV index.
        """

        if index is None or index < 0:
            return "N/A"

        elif index < 3:
            return "Low"

        elif index < 6:
            return "Moderate"

        elif index < 8:
            return "High"

        elif index < 11:
            return "Very high"

        else:
            return "Extreme"

    @staticmethod
    def _get_percentage(value: float) -> str:
        """Turn a value from 0 to 1 into a percentage.

        Args:
            value: the value to transform.

        Returns:
            A string with the percentage value and % symbol.
        """

        return "{}%".format(round(value * 100))

    @staticmethod
    def _get_date(timestamp: int, timezone: str) -> str:
        """Get a date from a timestamp, offset according to the provided timezone.

        Args:
            timestamp: a UNIX timestamp.
            timezone: the timezone of the timestamp.

        Returns:
            A string with the date at the timestamp.
        """

        return datetime.fromtimestamp(timestamp, pytz.timezone(timezone)).date().isoformat()

    @staticmethod
    def _get_time(timestamp: int, timezone: str) -> str:
        """Get a time from a timestamp, offset according to the provided timezone.

        Args:
            timestamp: a UNIX timestamp.
            timezone: the timezone of the timestamp.

        Returns:
            A string with the time at the timestamp.
        """

        return datetime.fromtimestamp(timestamp, pytz.timezone(timezone)).time().strftime("%H:%M")


if __name__ == "__main__":
    # Test the weather API

    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    logger.info("Forecast: " + json.dumps(Weather().get_forecast(), indent=2))
