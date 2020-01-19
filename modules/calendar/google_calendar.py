#!/usr/bin/python
# -*- coding:utf-8 -*-

import logging

# Silence Google's warnings
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
# Silence Google's resource fetching messages
logging.getLogger("googleapiclient.discovery").setLevel(logging.ERROR)

logger = logging.getLogger(__file__)
logger.info("Calendar powered by Google (https://developers.google.com/calendar)")

from datetime import datetime
import json
import os
import pickle
from typing import Any, Dict, List

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


class Calendar:
    """Google calendar API wrapper for getting events and normalise them."""

    _STATUS: Dict[str, str] = {"accepted": "yes", "declined": "no", "tentative": "maybe", "needsAction": "N/A"}
    """All possible event status."""

    def __init__(self):
        """Initialise the Google calendar library."""

        self._service = build("calendar", "v3", credentials=self._get_credentials())

        available_calendars = self.list_calendars()
        if len(available_calendars) < 1:
            raise RuntimeError("No calendars available")

        with open(os.path.join(os.path.dirname(__file__), "res/configuration.json"), "r") as file:
            configuration = json.load(file)
        self._calendars = configuration["calendars"]

        if self._calendars is None or len(self._calendars) < 1:
            raise RuntimeWarning("No calendars defined, there should be at least one calendar id. " +
                                 "Available calendar ids (and their names):\n - " +
                                 "\n - ".join("{} ({})".format(k, v) for k, v in available_calendars.items()))

        for calendar in self._calendars:
            if calendar not in available_calendars:
                raise RuntimeWarning("Invalid calendar id: {}. ".format(calendar) +
                                     "Available calendar ids (and their names):\n - " +
                                     "\n - ".join("{} ({})".format(k, v) for k, v in available_calendars.items()))

    def list_calendars(self) -> Dict[str, Any]:
        """List all available calendars in your account.

        Returns:
            A dictionary with calendar ids for keys, and their names as values.
        """

        logger.debug("Fetching available calendars")

        calendars = {}

        page_token = None
        while True:
            response = self._service.calendarList().list(maxResults=250, pageToken=page_token).execute()
            if "error" in response.keys():
                self._handle_error(response["error"])

            for entry in response["items"]:
                if entry.get("primary", False):
                    calendars["primary"] = entry["summary"]

                else:
                    calendars[entry["id"]] = entry["summary"]

            page_token = response.get("nextPageToken", None)
            if page_token is None:
                logger.debug("Calendars found: {}".format(calendars))

                return calendars

    def list_events(self, count: int = 1) -> List[Dict[str, Any]]:
        """List future events in the configured calendars, up to a certain count.

        Args:
            count: the maximum amount of events to get. The actual result might contain less that this value.

        Returns:
            A list of events, sorted from first to last.
        """

        logger.debug("Fetching upcoming events")

        if count < 0:
            raise ValueError("The event count must be a positive integer")

        elif count < 1:
            return []

        now: str = datetime.utcnow().isoformat() + "Z"
        events = {}
        for calendar in self._calendars:
            response: dict = self._service.events() \
                .list(calendarId=calendar, maxResults=count, timeMin=now, singleEvents=True, orderBy="startTime") \
                .execute()

            if "error" in response.keys():
                self._handle_error(response["error"])

            events[calendar] = list(map(self._normalise, response.get("items", [])))

        logger.debug("Events fetched")

        return sorted(sum(events.values(), []), key=self._event_sorter)[:count]

    @staticmethod
    def _normalise(source: Dict[str, Any]) -> Dict[str, Any]:
        """Create a normalised dictionary out of different event types.

        Args:
            source: a json with the information of the event, as a dictionary.

        Returns:
            A standardised event.
        """

        return {
            "title": source["summary"],
            "start": Calendar._normalise_date_time(source["start"]),
            "end": Calendar._normalise_date_time(source["end"]),
            "location": source.get("location", "N/A"),
            "status": next((Calendar._STATUS[attendee["responseStatus"]]
                            for attendee in source.get("attendees", [])
                            if attendee.get("self", False)), "yes"),
            "recurring": "recurringEventId" in source.keys(),
        }

    @staticmethod
    def _normalise_date_time(source: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise the json's date and time data.

        Args:
            source: a json which has the date and time as a dictionary.

        Returns:
            A new dictionary with separate entries for date, time, and time zone.
        """

        date_time = {}
        if "date" in source.keys():
            date_time["date"] = source["date"]

        elif "dateTime" in source.keys():
            date_time["date"] = source["dateTime"][:10]
            date_time["time"] = source["dateTime"][11:16]

        else:
            raise ValueError("Unexpected argument format.\nDetail: {}"
                             .format(json.dumps(source, indent=2, sort_keys=True)))

        if len(date_time.get("time", "")) == 0:
            date_time["time"] = "N/A"

        return date_time

    @staticmethod
    def _get_credentials() -> Credentials:
        """Get the credentials required to connect to Google Calendar API.

        Returns:
            The credentials used to connect to Google's API.
        """

        logger.debug("Load credentials")

        credentials = None
        scopes = "https://www.googleapis.com/auth/calendar.readonly"

        path = os.path.dirname(__file__)
        token_path = os.path.join(path, "res/token.pickle")
        credentials_path = os.path.join(path, "res/credentials.json")

        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())

            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
                credentials = flow.run_local_server()

            with open(token_path, "wb") as token:
                pickle.dump(credentials, token)

        logger.debug("Credentials loaded")

        return credentials

    @staticmethod
    def _handle_error(error: Dict[str, Any]):
        """Raise an error based on the received error response.

        Args:
            error: an error response from the Google calendar API.
        """

        raise ResourceWarning("{} {}\nDetail: {}".format(error["code"], error["message"], json))

    @staticmethod
    def _event_sorter(event: Dict[str, Any]) -> str:
        """Get the sorting key for an event.

        Args:
            event: a dictionary representing the event.

        Returns:
            A string that when compared to another event's will allow to sort them.
        """

        if event["start"]["time"] == "N/A":
            return "{}T00:00:00".format(event["start"]["date"])

        else:
            return "{}T{}:00".format(event["start"]["date"], event["start"]["time"])


if __name__ == "__main__":
    # Test the calendar API

    import sys

    logging.getLogger().setLevel(logging.NOTSET)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter("[{levelname:s}] {message:s}", style="{"))
    logging.getLogger().addHandler(console)

    logger.info("Agenda: " + json.dumps(Calendar().list_events(100), indent=2))
