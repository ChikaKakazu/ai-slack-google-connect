"""Slack interactive component handler (buttons, actions)."""

import json
import logging

from slack_bolt import App

from services.calendar_service import CalendarService
from services.token_service import TokenService
from utils.slack_utils import build_event_created_blocks
from utils.time_utils import parse_datetime

logger = logging.getLogger(__name__)

token_service = TokenService()


def register_interactive_handlers(app: App) -> None:
    """Register interactive action handlers on the Slack Bolt app."""

    # Register handlers for slot confirmation buttons (confirm_slot_0 through confirm_slot_4)
    for i in range(5):
        action_id = f"confirm_slot_{i}"
        app.action(action_id)(_handle_confirm_slot)

    app.action("google_oauth")(_handle_oauth_button)


def _handle_confirm_slot(ack, body, client, say) -> None:
    """Handle slot confirmation button click.

    Creates the calendar event with the selected time slot.
    """
    ack()

    user_id = body["user"]["id"]
    channel = body["channel"]["id"]
    action = body["actions"][0]

    try:
        slot_data = json.loads(action["value"])
    except (json.JSONDecodeError, KeyError):
        logger.error("Invalid slot data in action value")
        say(text="エラー: 無効なデータです。", channel=channel)
        return

    # Get user credentials
    credentials = token_service.get_credentials(user_id)
    if not credentials:
        say(text="Google Calendarの認証が期限切れです。再度認証してください。", channel=channel)
        return

    calendar = CalendarService(credentials)

    try:
        start_time = parse_datetime(slot_data["start"])
        end_time = parse_datetime(slot_data["end"])
        attendees = slot_data["attendees"]
        summary = slot_data.get("summary", "ミーティング")

        event = calendar.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
        )

        event_data = {
            "summary": event["summary"],
            "start": event["start"]["dateTime"],
            "end": event["end"]["dateTime"],
            "attendees": [a["email"] for a in event.get("attendees", [])],
            "html_link": event.get("htmlLink", ""),
        }

        blocks = build_event_created_blocks(event_data)

        # Update the original message to show confirmation
        client.chat_update(
            channel=channel,
            ts=body["message"]["ts"],
            blocks=blocks,
            text=f"✅ {summary} を作成しました",
        )

    except Exception:
        logger.exception("Failed to create event from slot confirmation")
        say(text="イベントの作成中にエラーが発生しました。再度お試しください。", channel=channel)


def _handle_oauth_button(ack, body) -> None:
    """Handle OAuth button click (just acknowledge - actual redirect happens via URL)."""
    ack()
