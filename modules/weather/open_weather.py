#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)
logger.info("Weather powered by Open Weather Map (https://openweathermap.org/)")

from datetime import datetime
import json
import os
import pytz
import requests
from typing import Any, Dict, Union


class Weather:
    """Open Weather Map API wrapper."""

    _COMPASS_ROSE = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    """A compass rose used to define which direction the wind is blowing from."""

    def __init__(self):
        """Load configuration from file and initialise."""

        with open(os.path.join(os.path.dirname(__file__), "res/credentials.json"), "r") as file:
            credentials = json.load(file)

        with open(os.path.join(os.path.dirname(__file__), "res/configuration.json"), "r") as file:
            configuration = json.load(file)

        self._query_headers = {"Accept-Encoding": "gzip"}
        self._query_parameters = {"lang": "en_gb", "units": "metric", "appid": credentials["api_key"],
                                  "lat": configuration["latitude"], "lon": configuration["longitude"]}
        self._url = "https://api.openweathermap.org/data/2.5/onecall"

    def get_forecast(self) -> Dict[str, Any]:
        """Get the forecast from the weather API and normalise it.

        Returns:
            A dictionary with the information of current and upcoming weather.
        """

        logger.debug("Fetching forecast")

        try:
            response = requests.get(self._url, headers=self._query_headers, params=self._query_parameters,
                                    timeout=(10, 10))

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
                "date": Weather._get_date(data["current"]["dt"], data["timezone"]),
                "time": Weather._get_time(data["current"]["dt"], data["timezone"]),
                "description": data["current"]["weather"][0]["description"],
                "id": data["current"]["weather"][0]["icon"],

                "temperature": round(data["current"]["temp"]),
                "feels like": round(data["current"]["feels_like"]),

                "clouds": Weather._get_percentage(data["current"].get("clouds", 0)),
                "pressure": data["current"].get("pressure", None),
                "wind": {
                    "speed": round(data["current"].get("wind_speed", 0)),
                    "direction": Weather._get_direction(data["current"].get("wind_deg", None)),
                },

                "humidity": Weather._get_percentage(data["current"].get("humidity", 0)),

                "uv index": Weather._get_uv_index(data["current"]["uvi"]),
            },
            "forecast": {
                "daily": [
                    {
                        "date": Weather._get_date(data["daily"][i]["dt"], data["timezone"]),
                        "description": data["daily"][i]["weather"][0]["description"],
                        "id": data["daily"][i]["weather"][0]["icon"],

                        "temperature": {
                            "min": round(data["daily"][i]["temp"]["min"]),
                            "max": round(data["daily"][i]["temp"]["max"]),
                        },

                        "clouds": Weather._get_percentage(data["daily"][i].get("clouds", 0)),
                        "pressure": data["daily"][i].get("pressure", None),
                        "wind": {
                            "speed": round(data["daily"][i].get("wind_speed", 0)),
                            "direction": Weather._get_direction(data["daily"][i].get("wind_deg", None)),
                        },

                        "humidity": Weather._get_percentage(data["daily"][i].get("humidity", 0)),

                        "sunrise": Weather._get_time(data["daily"][i]["sunrise"], data["timezone"]),
                        "sunset": Weather._get_time(data["daily"][i]["sunset"], data["timezone"]),

                    } for i in range(len(data["daily"]))
                ],
                "hourly": [
                    {
                        "date": Weather._get_date(data["hourly"][i]["dt"], data["timezone"]),
                        "time": Weather._get_time(data["hourly"][i]["dt"], data["timezone"]),
                        "description": data["hourly"][i]["weather"][0]["description"],
                        "id": data["hourly"][i]["weather"][0]["icon"],

                        "temperature": round(data["hourly"][i]["temp"]),

                        "clouds": Weather._get_percentage(data["hourly"][i].get("clouds", 0)),
                        "pressure": data["hourly"][i].get("pressure", None),
                        "wind": {
                            "speed": round(data["hourly"][i].get("wind_speed", 0)),
                            "direction": Weather._get_direction(data["hourly"][i].get("wind_deg", None)),
                        },

                        "humidity": Weather._get_percentage(data["hourly"][i].get("humidity", 0)),

                    } for i in range(len(data["hourly"]))
                ],
            },
        }

    @staticmethod
    def _get_direction(degrees: float) -> Union[str, None]:
        """Get the cardinal direction from where the wind is blowing.

        Args:
            degrees: the angle at which the wind is blowing from, with the north as zero, and increasing clock-wise.

        Returns:
            A string for the abbreviation of the direction.
        """

        if degrees is None:
            return None

        else:
            return Weather._COMPASS_ROSE[round((degrees % 360) / 22.5)]

    @staticmethod
    def _get_uv_index(index: int) -> Union[str, None]:
        """Get a human readable name for the given UV index.

        Args:
            index: the index value being transformed.

        Returns:
            A string with the severity of the UV index.
        """

        if index is None or index < 0:
            return None

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

        return "{}%".format(round(value))

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
