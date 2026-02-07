"""Slack Block Kit UI generation utilities."""

import json
import logging
import re
from datetime import datetime

from utils.time_utils import parse_datetime

logger = logging.getLogger(__name__)


def build_free_slots_blocks(
    slots: list[dict],
    attendees: list[str],
    summary: str = "ミーティング",
    duration_minutes: int = 30,
) -> list[dict]:
    """Build Block Kit blocks for displaying free time slot options.

    Args:
        slots: List of {"start": str, "end": str} time slots.
        attendees: List of attendee emails.
        summary: Meeting title.
        duration_minutes: Meeting duration.

    Returns:
        List of Slack Block Kit blocks.
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📅 {summary} - 空き時間候補",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*参加者:* {', '.join(attendees)}\n"
                    f"*所要時間:* {duration_minutes}分\n"
                    f"*候補数:* {len(slots)}件"
                ),
            },
        },
        {"type": "divider"},
    ]

    # Show up to 5 candidates
    display_slots = slots[:5]

    for i, slot in enumerate(display_slots):
        start_dt = parse_datetime(slot["start"])
        end_dt = parse_datetime(slot["end"])

        time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"

        action_value = json.dumps({
            "action": "confirm_slot",
            "start": slot["start"],
            "end": slot["end"],
            "attendees": attendees,
            "summary": summary,
        }, ensure_ascii=False)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*候補 {i + 1}:* {time_str}",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "この時間で予約",
                },
                "action_id": f"confirm_slot_{i}",
                "value": action_value,
                "style": "primary",
            },
        })

    if len(slots) > 5:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"他にも {len(slots) - 5} 件の候補があります。",
                }
            ],
        })

    return blocks


def build_schedule_suggestion_blocks(result_data: dict) -> list[dict]:
    """Build Block Kit blocks for schedule suggestion candidates.

    Args:
        result_data: Result data from search_free_slots tool (with status: suggest_schedule).

    Returns:
        List of Slack Block Kit blocks.
    """
    summary = result_data.get("summary", "ミーティング")
    attendees = result_data.get("attendees", [])
    duration = result_data.get("duration_minutes", 60)
    slots = result_data.get("slots", [])

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📅 {summary} - 空き時間候補",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*参加者:* {', '.join(attendees)}\n"
                    f"*所要時間:* {duration}分\n"
                    f"*候補数:* {len(slots)}件"
                ),
            },
        },
        {"type": "divider"},
    ]

    # Show up to 5 candidates
    display_slots = slots[:5]

    for i, slot in enumerate(display_slots):
        start_dt = parse_datetime(slot["start"])
        end_dt = parse_datetime(slot["end"])

        time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"

        action_value = json.dumps({
            "action": "confirm_slot",
            "start": slot["start"],
            "end": slot["end"],
            "attendees": attendees,
            "summary": summary,
        }, ensure_ascii=False)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*候補 {i + 1}:* {time_str}",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "この時間で予約",
                },
                "action_id": f"confirm_slot_{i}",
                "value": action_value,
                "style": "primary",
            },
        })

    if len(slots) > 5:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"他にも {len(slots) - 5} 件の候補があります。",
                }
            ],
        })

    return blocks


def build_reschedule_suggestion_blocks(result_data: dict) -> list[dict]:
    """Build Block Kit blocks for reschedule suggestion candidates.

    Args:
        result_data: Result data from suggest_reschedule tool.

    Returns:
        List of Slack Block Kit blocks.
    """
    summary = result_data.get("summary", "ミーティング")
    attendees = result_data.get("attendees", [])
    duration = result_data.get("duration_minutes", 60)
    candidates = result_data.get("candidates", [])
    fallback_used = result_data.get("fallback_used", False)
    event_id = result_data.get("event_id", "")

    # Original time
    original_start = result_data.get("original_start", "")
    original_end = result_data.get("original_end", "")
    original_time_str = ""
    if original_start and original_end:
        orig_s = parse_datetime(original_start)
        orig_e = parse_datetime(original_end)
        original_time_str = f"{orig_s.strftime('%m/%d %H:%M')} - {orig_e.strftime('%H:%M')}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔄 {summary} - リスケジュール候補",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*元の時間:* {original_time_str}\n"
                    f"*参加者:* {', '.join(attendees)}\n"
                    f"*所要時間:* {duration}分"
                ),
            },
        },
        {"type": "divider"},
    ]

    if fallback_used:
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": "⚠️ 指定日に空きがなかったため、翌営業日の候補を表示しています。",
            }],
        })

    for i, candidate in enumerate(candidates):
        start_dt = parse_datetime(candidate["start"])
        end_dt = parse_datetime(candidate["end"])
        time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"

        action_value = json.dumps({
            "action": "confirm_reschedule",
            "event_id": event_id,
            "start": candidate["start"],
            "end": candidate["end"],
            "summary": summary,
        }, ensure_ascii=False)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*候補 {i + 1}:* {time_str}",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "この時間に変更",
                },
                "action_id": f"confirm_reschedule_{i}",
                "value": action_value,
                "style": "primary",
            },
        })

    return blocks


def build_event_created_blocks(event_data: dict) -> list[dict]:
    """Build Block Kit blocks for event creation confirmation.

    Args:
        event_data: Event data from calendar API.

    Returns:
        List of Slack Block Kit blocks.
    """
    start_dt = parse_datetime(event_data["start"])
    end_dt = parse_datetime(event_data["end"])
    time_str = f"{start_dt.strftime('%Y/%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "✅ イベントを作成しました",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{event_data['summary']}*\n"
                    f"📅 {time_str}\n"
                    f"👥 {', '.join(event_data.get('attendees', []))}"
                ),
            },
        },
    ]

    html_link = event_data.get("html_link")
    if html_link:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<{html_link}|Google Calendarで確認>",
            },
        })

    return blocks


def build_oauth_prompt_blocks(oauth_url: str) -> list[dict]:
    """Build Block Kit blocks prompting user to authenticate with Google.

    Args:
        oauth_url: Google OAuth authorization URL.

    Returns:
        List of Slack Block Kit blocks.
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Google Calendarへのアクセス許可が必要です。下のボタンから認証してください。",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Google認証",
                },
                "url": oauth_url,
                "action_id": "google_oauth",
                "style": "primary",
            },
        },
    ]


def build_slot_confirmation_modal(
    slot_data: dict, channel_id: str, message_ts: str
) -> dict:
    """Build a modal view for slot confirmation with event name input.

    Args:
        slot_data: Slot data containing start, end, attendees, summary.
        channel_id: Slack channel ID for updating the original message.
        message_ts: Timestamp of the original message.

    Returns:
        Slack modal view definition dict.
    """
    start_dt = parse_datetime(slot_data["start"])
    end_dt = parse_datetime(slot_data["end"])
    time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"
    attendees = slot_data.get("attendees", [])
    summary = slot_data.get("summary", "ミーティング")

    private_metadata = json.dumps({
        "start": slot_data["start"],
        "end": slot_data["end"],
        "attendees": attendees,
        "channel_id": channel_id,
        "message_ts": message_ts,
    }, ensure_ascii=False)

    return {
        "type": "modal",
        "callback_id": "slot_confirmation_modal",
        "title": {"type": "plain_text", "text": "予約確認"},
        "submit": {"type": "plain_text", "text": "予約する"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "private_metadata": private_metadata,
        "blocks": [
            {
                "type": "input",
                "block_id": "summary_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "summary_input",
                    "initial_value": summary,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "イベント名を入力",
                    },
                },
                "label": {"type": "plain_text", "text": "イベント名"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📅 {time_str}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"👥 {', '.join(attendees)}",
                },
            },
        ],
    }


def build_create_confirmation_blocks(result_data: dict) -> list[dict]:
    """Build Block Kit blocks for AI-created event confirmation with a button.

    Args:
        result_data: Result data from create_event tool (with status: suggest_create).

    Returns:
        List of Slack Block Kit blocks.
    """
    summary = result_data.get("summary", "ミーティング")
    start_dt = parse_datetime(result_data["start_time"])
    end_dt = parse_datetime(result_data["end_time"])
    time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"
    attendees = result_data.get("attendees", [])

    action_value = json.dumps({
        "action": "confirm_create",
        "summary": summary,
        "start_time": result_data["start_time"],
        "end_time": result_data["end_time"],
        "attendees": attendees,
        "description": result_data.get("description", ""),
    }, ensure_ascii=False)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📅 {summary} - イベント作成確認",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*時間:* {time_str}\n"
                    f"*参加者:* {', '.join(attendees)}"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "予約する",
                    },
                    "action_id": "confirm_create",
                    "value": action_value,
                    "style": "primary",
                },
            ],
        },
    ]

    return blocks


def build_create_confirmation_modal(
    create_data: dict, channel_id: str, message_ts: str
) -> dict:
    """Build a modal view for create event confirmation with event name input.

    Args:
        create_data: Create data containing summary, start_time, end_time, attendees, description.
        channel_id: Slack channel ID for updating the original message.
        message_ts: Timestamp of the original message.

    Returns:
        Slack modal view definition dict.
    """
    start_dt = parse_datetime(create_data["start_time"])
    end_dt = parse_datetime(create_data["end_time"])
    time_str = f"{start_dt.strftime('%m/%d %H:%M')} - {end_dt.strftime('%H:%M')}"
    attendees = create_data.get("attendees", [])
    summary = create_data.get("summary", "ミーティング")

    private_metadata = json.dumps({
        "start_time": create_data["start_time"],
        "end_time": create_data["end_time"],
        "attendees": attendees,
        "description": create_data.get("description", ""),
        "channel_id": channel_id,
        "message_ts": message_ts,
    }, ensure_ascii=False)

    return {
        "type": "modal",
        "callback_id": "create_confirmation_modal",
        "title": {"type": "plain_text", "text": "予約確認"},
        "submit": {"type": "plain_text", "text": "予約する"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "private_metadata": private_metadata,
        "blocks": [
            {
                "type": "input",
                "block_id": "summary_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "summary_input",
                    "initial_value": summary,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "イベント名を入力",
                    },
                },
                "label": {"type": "plain_text", "text": "イベント名"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📅 {time_str}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"👥 {', '.join(attendees)}",
                },
            },
        ],
    }


def resolve_user_mentions(text: str, client) -> str:
    """Replace Slack user mentions (<@USER_ID>) with their email addresses.

    Args:
        text: Message text possibly containing <@USER_ID> mentions.
        client: Slack WebClient instance.

    Returns:
        Text with user mentions replaced by email addresses.
    """
    mention_pattern = re.compile(r"<@([A-Z0-9]+)>")
    matches = mention_pattern.findall(text)

    if not matches:
        return text

    for user_id in matches:
        try:
            response = client.users_info(user=user_id)
            email = response["user"]["profile"].get("email")
            if email:
                text = text.replace(f"<@{user_id}>", email)
            else:
                logger.warning("No email found for user=%s", user_id)
        except Exception:
            logger.exception("Failed to resolve email for user=%s", user_id)

    return text
