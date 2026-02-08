"""Slack interactive component handler (buttons, actions)."""

import json
import logging

from slack_bolt import App

from services.calendar_service import CalendarService
from services.token_service import TokenService
from utils.slack_utils import (
    build_create_confirmation_modal,
    build_event_created_blocks,
    build_slot_confirmation_modal,
    post_attendee_mentions,
)
from utils.time_utils import parse_datetime

logger = logging.getLogger(__name__)

token_service = TokenService()


def register_interactive_handlers(app: App) -> None:
    """Register interactive action handlers on the Slack Bolt app."""

    # Register handlers for slot confirmation buttons (confirm_slot_0 through confirm_slot_4)
    for i in range(5):
        action_id = f"confirm_slot_{i}"
        app.action(action_id)(_handle_confirm_slot)

    # Register handlers for reschedule confirmation buttons (confirm_reschedule_0 through confirm_reschedule_2)
    for i in range(3):
        action_id = f"confirm_reschedule_{i}"
        app.action(action_id)(_handle_confirm_reschedule)

    app.action("google_oauth")(_handle_oauth_button)
    app.action("confirm_create")(_handle_confirm_create)

    # Register modal submission handlers
    app.view("slot_confirmation_modal")(_handle_slot_modal_submit)
    app.view("create_confirmation_modal")(_handle_create_modal_submit)


def _handle_confirm_slot(ack, body, client, say) -> None:
    """Handle slot confirmation button click.

    Opens a modal for the user to confirm/edit the event name before creating.
    """
    ack()

    channel = body["channel"]["id"]
    action = body["actions"][0]

    try:
        slot_data = json.loads(action["value"])
    except (json.JSONDecodeError, KeyError):
        logger.error("Invalid slot data in action value")
        say(text="エラー: 無効なデータです。", channel=channel)
        return

    trigger_id = body.get("trigger_id")
    if not trigger_id:
        logger.error("No trigger_id in body")
        say(text="エラー: モーダルを開けませんでした。", channel=channel)
        return

    message_ts = body["message"]["ts"]
    modal = build_slot_confirmation_modal(slot_data, channel, message_ts)

    try:
        client.views_open(trigger_id=trigger_id, view=modal)
    except Exception:
        logger.exception("Failed to open slot confirmation modal")
        say(text="モーダルを開けませんでした。再度お試しください。", channel=channel)


def _handle_slot_modal_submit(ack, body, client, view) -> None:
    """Handle slot confirmation modal submission.

    Creates the calendar event with the user-specified event name.
    """
    ack()

    user_id = body["user"]["id"]

    try:
        metadata = json.loads(view["private_metadata"])
    except (json.JSONDecodeError, KeyError):
        logger.error("Invalid private_metadata in modal submission")
        return

    channel_id = metadata["channel_id"]
    message_ts = metadata["message_ts"]
    summary = view["state"]["values"]["summary_block"]["summary_input"]["value"]

    credentials = token_service.get_credentials(user_id)
    if not credentials:
        try:
            client.chat_postMessage(
                channel=channel_id,
                text="Google Calendarの認証が期限切れです。再度認証してください。",
            )
        except Exception:
            logger.exception("Failed to send auth error message")
        return

    calendar = CalendarService(credentials)

    try:
        start_time = parse_datetime(metadata["start"])
        end_time = parse_datetime(metadata["end"])
        attendees = metadata["attendees"]

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

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=blocks,
            text=f"✅ {summary} を作成しました",
        )

        post_attendee_mentions(
            client, channel_id, message_ts, summary, event_data["attendees"]
        )

    except Exception:
        logger.exception("Failed to create event from modal submission")
        try:
            client.chat_postMessage(
                channel=channel_id,
                text="イベントの作成中にエラーが発生しました。再度お試しください。",
            )
        except Exception:
            logger.exception("Failed to send error message")


def _handle_confirm_reschedule(ack, body, client, say) -> None:
    """Handle reschedule confirmation button click.

    Reschedules the calendar event to the selected time slot.
    """
    ack()

    user_id = body["user"]["id"]
    channel = body["channel"]["id"]
    action = body["actions"][0]

    try:
        reschedule_data = json.loads(action["value"])
    except (json.JSONDecodeError, KeyError):
        logger.error("Invalid reschedule data in action value")
        say(text="エラー: 無効なデータです。", channel=channel)
        return

    credentials = token_service.get_credentials(user_id)
    if not credentials:
        say(text="Google Calendarの認証が期限切れです。再度認証してください。", channel=channel)
        return

    calendar = CalendarService(credentials)

    try:
        new_start = parse_datetime(reschedule_data["start"])
        new_end = parse_datetime(reschedule_data["end"])
        event_id = reschedule_data["event_id"]
        summary = reschedule_data.get("summary", "ミーティング")

        updated = calendar.reschedule_event(
            event_id=event_id,
            new_start=new_start,
            new_end=new_end,
        )

        start_str = parse_datetime(updated["start"]["dateTime"]).strftime("%m/%d %H:%M")
        end_str = parse_datetime(updated["end"]["dateTime"]).strftime("%H:%M")

        attendees = [a["email"] for a in updated.get("attendees", [])]
        reschedule_ts = body["message"]["ts"]

        client.chat_update(
            channel=channel,
            ts=reschedule_ts,
            blocks=[
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "✅ リスケジュール完了"},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{summary}*\n"
                            f"📅 {start_str} - {end_str}\n"
                            f"<{updated.get('htmlLink', '')}|Google Calendarで確認>"
                        ),
                    },
                },
            ],
            text=f"✅ {summary} をリスケジュールしました",
        )

        post_attendee_mentions(
            client, channel, reschedule_ts, summary, attendees
        )

    except Exception:
        logger.exception("Failed to reschedule event from confirmation")
        say(text="リスケジュール中にエラーが発生しました。再度お試しください。", channel=channel)


def _handle_confirm_create(ack, body, client, say) -> None:
    """Handle create event confirmation button click.

    Opens a modal for the user to confirm/edit the event name before creating.
    """
    ack()

    channel = body["channel"]["id"]
    action = body["actions"][0]

    try:
        create_data = json.loads(action["value"])
    except (json.JSONDecodeError, KeyError):
        logger.error("Invalid create data in action value")
        say(text="エラー: 無効なデータです。", channel=channel)
        return

    trigger_id = body.get("trigger_id")
    if not trigger_id:
        logger.error("No trigger_id in body")
        say(text="エラー: モーダルを開けませんでした。", channel=channel)
        return

    message_ts = body["message"]["ts"]
    modal = build_create_confirmation_modal(create_data, channel, message_ts)

    try:
        client.views_open(trigger_id=trigger_id, view=modal)
    except Exception:
        logger.exception("Failed to open create confirmation modal")
        say(text="モーダルを開けませんでした。再度お試しください。", channel=channel)


def _handle_create_modal_submit(ack, body, client, view) -> None:
    """Handle create event confirmation modal submission.

    Creates the calendar event with the user-specified event name.
    """
    ack()

    user_id = body["user"]["id"]

    try:
        metadata = json.loads(view["private_metadata"])
    except (json.JSONDecodeError, KeyError):
        logger.error("Invalid private_metadata in create modal submission")
        return

    channel_id = metadata["channel_id"]
    message_ts = metadata["message_ts"]
    summary = view["state"]["values"]["summary_block"]["summary_input"]["value"]

    credentials = token_service.get_credentials(user_id)
    if not credentials:
        try:
            client.chat_postMessage(
                channel=channel_id,
                text="Google Calendarの認証が期限切れです。再度認証してください。",
            )
        except Exception:
            logger.exception("Failed to send auth error message")
        return

    calendar = CalendarService(credentials)

    try:
        start_time = parse_datetime(metadata["start_time"])
        end_time = parse_datetime(metadata["end_time"])
        attendees = metadata["attendees"]
        description = metadata.get("description", "")

        event = calendar.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            description=description,
        )

        event_data = {
            "summary": event["summary"],
            "start": event["start"]["dateTime"],
            "end": event["end"]["dateTime"],
            "attendees": [a["email"] for a in event.get("attendees", [])],
            "html_link": event.get("htmlLink", ""),
        }

        blocks = build_event_created_blocks(event_data)

        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            blocks=blocks,
            text=f"✅ {summary} を作成しました",
        )

        post_attendee_mentions(
            client, channel_id, message_ts, summary, event_data["attendees"]
        )

    except Exception:
        logger.exception("Failed to create event from create modal submission")
        try:
            client.chat_postMessage(
                channel=channel_id,
                text="イベントの作成中にエラーが発生しました。再度お試しください。",
            )
        except Exception:
            logger.exception("Failed to send error message")


def _handle_oauth_button(ack, body) -> None:
    """Handle OAuth button click (just acknowledge - actual redirect happens via URL)."""
    ack()
