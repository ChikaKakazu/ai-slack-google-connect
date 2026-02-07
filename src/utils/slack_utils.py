"""Slack Block Kit UI generation utilities."""

import json
from datetime import datetime

from utils.time_utils import parse_datetime


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
