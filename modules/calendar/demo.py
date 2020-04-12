#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

logger = logging.getLogger(__file__)

import json
from typing import Any, Dict, List


class Calendar:
    """Demo calendar wrapper, used to create example image."""

    @staticmethod
    def list_calendars() -> Dict[str, Any]:
        """List all demo available calendars in your account.

        Returns:
            A dictionary with demo calendar ids for keys, and their names as values.
        """

        return {
            "primary": "example@gmail.com",
            "en.usa#holiday@group.v.calendar.google.com": "Holidays in USA",
        }

    def list_events(self, count: int = 1) -> List[Dict[str, Any]]:
        """List demo events, up to a certain count.

        Args:
            count: the maximum amount of events to get. The actual result might contain less that this value.

        Returns:
            A list of demo events, sorted from first to last.
        """

        events: List[Dict[str, Any]] = []

        # Add different status
        for date, status in [("2020-01-{:02d}".format(x + 1), status) for x, status in
                             enumerate(["yes", "maybe", None, "no"])]:
            events.append({
                "title": {
                    "yes": "Accepted event",
                    "maybe": "Tentative event",
                    None: "Unconfirmed event",
                    "no": "Declined event",
                }[status],
                "description": {
                    "yes": "(Answer: Yes)",
                    "maybe": "(Answer: Maybe)",
                    None: "(Answer: N/A)",
                    "no": "(Answer: No)",
                }[status],
                "start": {
                    "date": date,
                    "time": "09:00",
                },
                "end": {
                    "date": date,
                    "time": "13:00",
                },
                "location": None,
                "status": status,
                "recurring": False,
            })

        # Add all day event
        events.append({
            "title": "All day event",
            "description": None,
            "start": {
                "date": "2020-02-01",
                "time": None,
            },
            "end": {
                "date": "2020-02-02",
                "time": None,
            },
            "location": None,
            "status": "yes",
            "recurring": False,
        })

        # Add long event message
        events.append({
                "title": "Event whose title does not fit in one line",
                "description": None,
                "start": {
                    "date": "2020-03-01",
                    "time": None,
                },
                "end": {
                    "date": "2020-03-01",
                    "time": None,
                },
                "location": None,
                "status": "yes",
                "recurring": False,
            })

        # Add several events on the same day
        for x in range(3):
            events.append({
                "title": "Same day event #{:02d}".format(x + 1),
                "description": None,
                "start": {
                    "date": "2020-04-01",
                    "time": [
                        "09:00",
                        "10:00",
                        "11:00",
                    ][x],
                },
                "end": {
                    "date": "2020-04-01",
                    "time": [
                        "10:00",
                        "11:00",
                        "12:00",
                    ][x],
                },
                "location": None,
                "status": "yes",
                "recurring": False,
            })

        events.append({
            "title": "Event with description",
            "description": "This is a description.",
            "start": {
                "date": "2020-05-01",
                "time": None,
            },
            "end": {
                "date": "2020-05-02",
                "time": None,
            },
            "location": None,
            "status": "yes",
            "recurring": False,
        })

        events.append({
            "title": "Event with location",
            "description": None,
            "start": {
                "date": "2020-06-01",
                "time": None,
            },
            "end": {
                "date": "2020-06-02",
                "time": None,
            },
            "location": "Bat Cave, NC 28792, USA",
            "status": "yes",
            "recurring": False,
        })

        events.append({
            "title": "Event with description and location",
            "description": "This is a description.",
            "start": {
                "date": "2020-07-01",
                "time": None,
            },
            "end": {
                "date": "2020-07-02",
                "time": None,
            },
            "location": "Bat Cave, NC 28792, USA",
            "status": "yes",
            "recurring": False,
        })

        events.append({
            "title": "Event with long description",
            "description": "This is a rather long description.",
            "start": {
                "date": "2020-08-01",
                "time": None,
            },
            "end": {
                "date": "2020-08-02",
                "time": None,
            },
            "location": None,
            "status": "yes",
            "recurring": False,
        })

        events.append({
            "title": "Event that falls off screen",
            "description": None,
            "start": {
                "date": "2020-09-01",
                "time": None,
            },
            "end": {
                "date": "2020-09-02",
                "time": None,
            },
            "location": None,
            "status": "yes",
            "recurring": False,
        })

        return sorted(events, key=self._event_sorter)[:count]

    @staticmethod
    def _event_sorter(event: Dict[str, Any]) -> str:
        """Get the sorting key for an event.

        Args:
            event: a dictionary representing the event.

        Returns:
            A string that when compared to another event's will allow to sort them.
        """

        if event["start"]["time"] is None:
            return "{}T00:00:00".format(event["start"]["date"])

        else:
            return "{}T{}:00".format(event["start"]["date"], event["start"]["time"])


if __name__ == "__main__":
    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    logger.info("Agenda: " + json.dumps(Calendar().list_events(100), indent=2))
