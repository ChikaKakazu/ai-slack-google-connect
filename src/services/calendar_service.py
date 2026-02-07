"""Google Calendar API operations."""

import logging
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from utils.time_utils import JST, find_free_slots, parse_datetime, to_rfc3339

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for Google Calendar API operations."""

    def __init__(self, credentials: Credentials):
        self.service = build("calendar", "v3", credentials=credentials)

    def get_freebusy(
        self,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime,
    ) -> dict[str, list[dict]]:
        """Query FreeBusy for multiple calendars.

        Args:
            calendar_ids: List of calendar IDs (email addresses).
            time_min: Start of query range.
            time_max: End of query range.

        Returns:
            Dict mapping calendar_id to list of busy periods.
        """
        body = {
            "timeMin": to_rfc3339(time_min),
            "timeMax": to_rfc3339(time_max),
            "timeZone": "Asia/Tokyo",
            "items": [{"id": cal_id} for cal_id in calendar_ids],
        }

        result = self.service.freebusy().query(body=body).execute()

        busy_map = {}
        for cal_id in calendar_ids:
            cal_data = result.get("calendars", {}).get(cal_id, {})
            busy_map[cal_id] = cal_data.get("busy", [])

        return busy_map

    def search_free_slots(
        self,
        calendar_ids: list[str],
        time_min: datetime,
        time_max: datetime,
        duration_minutes: int = 30,
    ) -> list[dict]:
        """Find free time slots across multiple calendars.

        Args:
            calendar_ids: List of calendar IDs.
            time_min: Start of search range.
            time_max: End of search range.
            duration_minutes: Required duration in minutes.

        Returns:
            List of available time slots.
        """
        busy_map = self.get_freebusy(calendar_ids, time_min, time_max)

        # Merge all busy periods
        all_busy = []
        for periods in busy_map.values():
            for period in periods:
                all_busy.append({
                    "start": parse_datetime(period["start"]),
                    "end": parse_datetime(period["end"]),
                })

        return find_free_slots(all_busy, time_min, time_max, duration_minutes)

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendees: list[str],
        description: str = "",
        calendar_id: str = "primary",
    ) -> dict:
        """Create a calendar event.

        Args:
            summary: Event title.
            start_time: Event start time.
            end_time: Event end time.
            attendees: List of attendee email addresses.
            description: Event description.
            calendar_id: Calendar to create event in.

        Returns:
            Created event resource.
        """
        event_body = {
            "summary": summary,
            "start": {
                "dateTime": to_rfc3339(start_time),
                "timeZone": "Asia/Tokyo",
            },
            "end": {
                "dateTime": to_rfc3339(end_time),
                "timeZone": "Asia/Tokyo",
            },
            "attendees": [{"email": email} for email in attendees],
        }

        if description:
            event_body["description"] = description

        event = self.service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all",
        ).execute()

        logger.info("Created event: %s (%s)", event["id"], summary)
        return event

    def reschedule_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        calendar_id: str = "primary",
    ) -> dict:
        """Reschedule an existing calendar event.

        Args:
            event_id: Google Calendar event ID.
            new_start: New start time.
            new_end: New end time.
            calendar_id: Calendar containing the event.

        Returns:
            Updated event resource.
        """
        event = self.service.events().get(
            calendarId=calendar_id,
            eventId=event_id,
        ).execute()

        event["start"] = {
            "dateTime": to_rfc3339(new_start),
            "timeZone": "Asia/Tokyo",
        }
        event["end"] = {
            "dateTime": to_rfc3339(new_end),
            "timeZone": "Asia/Tokyo",
        }

        updated = self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event,
            sendUpdates="all",
        ).execute()

        logger.info("Rescheduled event: %s", event_id)
        return updated
