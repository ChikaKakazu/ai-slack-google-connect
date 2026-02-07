"""Tool execution engine for Bedrock Claude Tool Use."""

import json
import logging
from datetime import datetime, timedelta

from services.calendar_service import CalendarService
from services.token_service import TokenService
from utils.time_utils import JST, get_date_range, is_business_day, next_business_day, now_jst, parse_datetime

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
            elif tool_name == "suggest_reschedule":
                return self._suggest_reschedule(calendar, tool_input)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
        except Exception as e:
            logger.exception("Tool execution error: %s", tool_name)
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _search_free_slots(self, calendar: CalendarService, tool_input: dict) -> str:
        """Execute search_free_slots tool."""
        attendees = tool_input["attendees"]
        date_str = tool_input.get("date", "今日")
        duration = tool_input.get("duration_minutes", 60)
        summary = tool_input.get("summary", "ミーティング")

        range_start, range_end = get_date_range(date_str)

        # Warn if searching on non-business day
        if not is_business_day(range_start.date()):
            return json.dumps({
                "status": "suggest_schedule",
                "warning": f"{date_str} は営業日外（土日祝）です。営業日を指定してください。",
                "slots": [],
                "busy_periods": [],
                "attendees": attendees,
                "date": date_str,
                "duration_minutes": duration,
                "summary": summary,
                "total_slots": 0,
            }, ensure_ascii=False)

        # Apply time constraints if specified
        time_min_str = tool_input.get("time_min")
        time_max_str = tool_input.get("time_max")

        if time_min_str:
            hour, minute = map(int, time_min_str.split(":"))
            range_start = range_start.replace(hour=hour, minute=minute)
        if time_max_str:
            hour, minute = map(int, time_max_str.split(":"))
            range_end = range_end.replace(hour=hour, minute=minute)

        slots, busy_periods = calendar.search_free_slots(
            calendar_ids=attendees,
            time_min=range_start,
            time_max=range_end,
            duration_minutes=duration,
        )

        return json.dumps({
            "status": "suggest_schedule",
            "slots": slots,
            "busy_periods": busy_periods,
            "attendees": attendees,
            "date": date_str,
            "duration_minutes": duration,
            "summary": summary,
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

    def _suggest_reschedule(self, calendar: CalendarService, tool_input: dict) -> str:
        """Execute suggest_reschedule tool.

        Fetches event details (by ID or title search), extracts attendees,
        searches for free slots, and returns up to 3 candidates.
        """
        event_id = tool_input.get("event_id")
        event_title = tool_input.get("event_title")

        if not event_id and not event_title:
            return json.dumps({
                "error": "event_id または event_title のいずれかを指定してください。",
            }, ensure_ascii=False)

        if event_id:
            event = calendar.get_event(event_id)
        else:
            try:
                events = calendar.search_events(event_title)
            except Exception as e:
                logger.exception("search_events failed for title=%s", event_title)
                return json.dumps({
                    "error": f"イベント検索中にエラーが発生しました: {e}",
                }, ensure_ascii=False)
            if not events:
                return json.dumps({
                    "error": f"「{event_title}」に一致するイベントが見つかりませんでした。タイトルを確認してください。",
                }, ensure_ascii=False)
            event = events[0]
            event_id = event["id"]
            logger.info("Found event by title: id=%s summary=%s", event_id, event.get("summary"))

        # Extract attendees; fall back to organizer/creator if no attendees listed
        attendees = [a["email"] for a in event.get("attendees", [])]
        if not attendees:
            organizer_email = event.get("organizer", {}).get("email")
            creator_email = event.get("creator", {}).get("email")
            fallback_email = organizer_email or creator_email
            if fallback_email:
                attendees = [fallback_email]
                logger.info("No attendees found, using organizer/creator: %s", fallback_email)
            else:
                return json.dumps({
                    "error": "このイベントには参加者・主催者の情報がありません。",
                }, ensure_ascii=False)

        # Calculate duration from original event
        event_start = parse_datetime(event["start"]["dateTime"])
        event_end = parse_datetime(event["end"]["dateTime"])
        duration = tool_input.get("duration_minutes") or int((event_end - event_start).total_seconds() / 60)

        # Determine target date
        date_str = tool_input.get("date")
        if date_str:
            range_start, range_end = get_date_range(date_str)
            target_date = range_start.date()
        else:
            target_date = event_start.date()
            range_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=JST)
            range_end = range_start + timedelta(days=1)

        # Ensure target is a business day
        if not is_business_day(target_date):
            target_date = next_business_day(target_date)
            range_start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=JST)
            range_end = range_start + timedelta(days=1)

        # Search the full day first (not limited by current time)
        slots, _ = calendar.search_free_slots(
            calendar_ids=attendees,
            time_min=range_start,
            time_max=range_end,
            duration_minutes=duration,
        )

        # If today, filter out past time slots
        current = now_jst()
        if target_date == current.date():
            slots = [s for s in slots if parse_datetime(s["start"]) >= current]

        # Exclude slots that overlap with the original event time
        # (proposing the same time as reschedule is not useful)
        orig_start_str = event["start"]["dateTime"]
        orig_end_str = event["end"]["dateTime"]
        slots = [
            s for s in slots
            if not (s["start"] == orig_start_str and s["end"] == orig_end_str)
        ]

        searched_date = target_date.isoformat()
        fallback_used = False

        # If not enough candidates on the same day, try next business day
        if len(slots) < 3:
            next_bd = next_business_day(target_date)
            next_start = datetime(next_bd.year, next_bd.month, next_bd.day, 0, 0, 0, tzinfo=JST)
            next_end = next_start + timedelta(days=1)

            next_slots, _ = calendar.search_free_slots(
                calendar_ids=attendees,
                time_min=next_start,
                time_max=next_end,
                duration_minutes=duration,
            )
            if next_slots:
                slots.extend(next_slots)
                fallback_used = not any(
                    parse_datetime(s["start"]).date() == target_date for s in slots[:3]
                )

        # Limit to 3 candidates
        candidates = slots[:3]

        if not candidates:
            return json.dumps({
                "status": "suggest_reschedule",
                "no_slots_found": True,
                "event_id": event_id,
                "summary": event.get("summary", ""),
                "attendees": attendees,
                "duration_minutes": duration,
                "searched_date": searched_date,
            }, ensure_ascii=False)

        return json.dumps({
            "status": "suggest_reschedule",
            "event_id": event_id,
            "summary": event.get("summary", ""),
            "original_start": event["start"]["dateTime"],
            "original_end": event["end"]["dateTime"],
            "attendees": attendees,
            "duration_minutes": duration,
            "candidates": candidates,
            "searched_date": searched_date,
            "fallback_used": fallback_used,
        }, ensure_ascii=False)
