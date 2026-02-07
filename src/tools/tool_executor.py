"""Tool execution engine for Bedrock Claude Tool Use."""

import json
import logging
from datetime import datetime

from services.calendar_service import CalendarService
from services.token_service import TokenService
from utils.time_utils import JST, get_date_range, parse_datetime

logger = logging.getLogger(__name__)

token_service = TokenService()


class ToolExecutor:
    """Executes tools requested by Bedrock Claude."""

    def execute(self, tool_name: str, tool_input: dict, user_id: str) -> str:
        """Execute a tool and return the result as a string.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Input parameters for the tool.
            user_id: Slack user ID (for OAuth credential lookup).

        Returns:
            JSON string result of the tool execution.
        """
        logger.info("Executing tool=%s input=%s", tool_name, json.dumps(tool_input, ensure_ascii=False)[:200])

        # Check for Google Calendar credentials
        credentials = token_service.get_credentials(user_id)
        if not credentials:
            return json.dumps({
                "error": "Google Calendarの認証が必要です。",
                "action": "oauth_required",
                "message": "ユーザーにGoogle Calendar認証リンクを案内してください。",
            }, ensure_ascii=False)

        calendar = CalendarService(credentials)

        try:
            if tool_name == "search_free_slots":
                return self._search_free_slots(calendar, tool_input)
            elif tool_name == "create_event":
                return self._create_event(calendar, tool_input)
            elif tool_name == "reschedule_event":
                return self._reschedule_event(calendar, tool_input)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
        except Exception as e:
            logger.exception("Tool execution error: %s", tool_name)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _search_free_slots(self, calendar: CalendarService, tool_input: dict) -> str:
        """Execute search_free_slots tool."""
        attendees = tool_input["attendees"]
        date_str = tool_input["date"]
        duration = tool_input.get("duration_minutes", 30)

        range_start, range_end = get_date_range(date_str)

        # Apply time constraints if specified
        time_min_str = tool_input.get("time_min")
        time_max_str = tool_input.get("time_max")

        if time_min_str:
            hour, minute = map(int, time_min_str.split(":"))
            range_start = range_start.replace(hour=hour, minute=minute)
        if time_max_str:
            hour, minute = map(int, time_max_str.split(":"))
            range_end = range_end.replace(hour=hour, minute=minute)

        slots = calendar.search_free_slots(
            calendar_ids=attendees,
            time_min=range_start,
            time_max=range_end,
            duration_minutes=duration,
        )

        return json.dumps({
            "slots": slots,
            "attendees": attendees,
            "date": date_str,
            "duration_minutes": duration,
            "total_slots": len(slots),
        }, ensure_ascii=False)

    def _create_event(self, calendar: CalendarService, tool_input: dict) -> str:
        """Execute create_event tool."""
        event = calendar.create_event(
            summary=tool_input["summary"],
            start_time=parse_datetime(tool_input["start_time"]),
            end_time=parse_datetime(tool_input["end_time"]),
            attendees=tool_input["attendees"],
            description=tool_input.get("description", ""),
        )

        return json.dumps({
            "event_id": event["id"],
            "html_link": event.get("htmlLink", ""),
            "summary": event["summary"],
            "start": event["start"]["dateTime"],
            "end": event["end"]["dateTime"],
            "attendees": [a["email"] for a in event.get("attendees", [])],
            "status": "created",
        }, ensure_ascii=False)

    def _reschedule_event(self, calendar: CalendarService, tool_input: dict) -> str:
        """Execute reschedule_event tool."""
        updated = calendar.reschedule_event(
            event_id=tool_input["event_id"],
            new_start=parse_datetime(tool_input["new_start_time"]),
            new_end=parse_datetime(tool_input["new_end_time"]),
        )

        return json.dumps({
            "event_id": updated["id"],
            "html_link": updated.get("htmlLink", ""),
            "summary": updated["summary"],
            "start": updated["start"]["dateTime"],
            "end": updated["end"]["dateTime"],
            "status": "rescheduled",
        }, ensure_ascii=False)
