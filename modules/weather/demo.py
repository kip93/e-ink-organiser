#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)

import json
from typing import Any, Dict


class Weather:
    """Demo weather wrapper."""

    @staticmethod
    def get_forecast() -> Dict[str, Any]:
        """Get demo forecast data.

        Returns:
            A dictionary with demo information of current and upcoming weather.
        """

        return {
            "now": {
                "time": "04:13",
                "id": "13n",
                "temperature": -13,
                "pressure": 1013.7,
                "humidity": "23%",
                "uv index": "Low",
            },
            "forecast": {
                "daily": [
                    {
                        "temperature": {
                            "max": 2,
                            "min": -14,
                        },
                        "humidity": "63%",
                        "sunrise": "07:38",
                        "sunset": "17:44",
                    },
                ],
                "hourly": [
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13d",
                    },
                    {
                        "id": "13d",
                    },
                    {
                        "id": "13d",
                    },
                    {
                        "id": "13d",
                    },
                    {
                        "id": "03d",
                    },
                    {
                        "id": "03d",
                    },
                    {
                        "id": "03d",
                    },
                    {
                        "id": "04d",
                    },
                    {
                        "id": "04d",
                    },
                    {
                        "id": "04d",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "13n",
                    },
                    {
                        "id": "04d",
                    },
                    {
                        "id": "01n",
                    },
                    {
                        "id": "01n",
                    },
                    {
                        "id": "01n",
                    },
                    {
                        "id": "01n",
                    },
                ],
            },
        }


if __name__ == "__main__":
    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    logger.info("Forecast: " + json.dumps(Weather().get_forecast(), indent=2))
