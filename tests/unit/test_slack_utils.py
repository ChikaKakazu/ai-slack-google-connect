"""Tests for slack_utils module."""

import json
from unittest.mock import MagicMock

from utils.slack_utils import (
    build_event_created_blocks,
    build_free_slots_blocks,
    build_oauth_prompt_blocks,
    build_reschedule_suggestion_blocks,
    build_schedule_suggestion_blocks,
    build_slot_confirmation_modal,
    resolve_user_mentions,
)


class TestBuildFreeSlotsBlocks:
    def test_basic_structure(self):
        slots = [
            {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"},
            {"start": "2024-01-15T15:00:00+09:00", "end": "2024-01-15T15:30:00+09:00"},
        ]
        blocks = build_free_slots_blocks(
            slots=slots,
            attendees=["a@test.com", "b@test.com"],
            summary="テストMTG",
        )

        # Header + info section + divider + 2 slots = 5 blocks
        assert len(blocks) == 5
        assert blocks[0]["type"] == "header"
        assert blocks[2]["type"] == "divider"

    def test_max_five_slots_shown(self):
        slots = [
            {"start": f"2024-01-15T{10+i}:00:00+09:00", "end": f"2024-01-15T{10+i}:30:00+09:00"}
            for i in range(7)
        ]
        blocks = build_free_slots_blocks(slots=slots, attendees=["a@test.com"])

        # Header + info + divider + 5 slots + context = 9
        assert len(blocks) == 9
        # Last block should be context about remaining
        assert blocks[-1]["type"] == "context"

    def test_button_action_data(self):
        slots = [{"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"}]
        blocks = build_free_slots_blocks(slots=slots, attendees=["a@test.com"], summary="MTG")

        button_block = blocks[3]
        action_value = json.loads(button_block["accessory"]["value"])
        assert action_value["action"] == "confirm_slot"
        assert action_value["attendees"] == ["a@test.com"]
        assert action_value["summary"] == "MTG"

    def test_empty_slots(self):
        blocks = build_free_slots_blocks(slots=[], attendees=["a@test.com"])
        # Header + info + divider = 3
        assert len(blocks) == 3


class TestBuildScheduleSuggestionBlocks:
    def test_basic_structure(self):
        result_data = {
            "status": "suggest_schedule",
            "slots": [
                {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"},
                {"start": "2024-01-15T15:00:00+09:00", "end": "2024-01-15T15:30:00+09:00"},
            ],
            "attendees": ["a@test.com", "b@test.com"],
            "summary": "企画会議",
            "duration_minutes": 30,
        }
        blocks = build_schedule_suggestion_blocks(result_data)

        # Header + info section + divider + 2 slots = 5 blocks
        assert len(blocks) == 5
        assert blocks[0]["type"] == "header"
        assert "企画会議" in blocks[0]["text"]["text"]
        assert "空き時間候補" in blocks[0]["text"]["text"]
        assert blocks[2]["type"] == "divider"

    def test_button_action_data(self):
        result_data = {
            "status": "suggest_schedule",
            "slots": [
                {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"},
            ],
            "attendees": ["a@test.com"],
            "summary": "MTG",
            "duration_minutes": 30,
        }
        blocks = build_schedule_suggestion_blocks(result_data)

        button_block = blocks[3]
        action_value = json.loads(button_block["accessory"]["value"])
        assert action_value["action"] == "confirm_slot"
        assert action_value["attendees"] == ["a@test.com"]
        assert action_value["summary"] == "MTG"
        assert button_block["accessory"]["action_id"] == "confirm_slot_0"

    def test_empty_slots(self):
        result_data = {
            "status": "suggest_schedule",
            "slots": [],
            "attendees": ["a@test.com"],
            "summary": "ミーティング",
            "duration_minutes": 60,
        }
        blocks = build_schedule_suggestion_blocks(result_data)
        # Header + info + divider = 3
        assert len(blocks) == 3

    def test_max_five_slots_with_context(self):
        result_data = {
            "status": "suggest_schedule",
            "slots": [
                {"start": f"2024-01-15T{10+i}:00:00+09:00", "end": f"2024-01-15T{10+i}:30:00+09:00"}
                for i in range(7)
            ],
            "attendees": ["a@test.com"],
            "summary": "ミーティング",
            "duration_minutes": 30,
        }
        blocks = build_schedule_suggestion_blocks(result_data)

        # Header + info + divider + 5 slots + context = 9
        assert len(blocks) == 9
        assert blocks[-1]["type"] == "context"

    def test_default_summary(self):
        result_data = {
            "status": "suggest_schedule",
            "slots": [
                {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"},
            ],
            "attendees": ["a@test.com"],
            "duration_minutes": 60,
        }
        blocks = build_schedule_suggestion_blocks(result_data)
        assert "ミーティング" in blocks[0]["text"]["text"]


class TestBuildRescheduleSuggestionBlocks:
    def test_basic_structure(self):
        result_data = {
            "event_id": "event123",
            "summary": "定例MTG",
            "original_start": "2024-01-15T14:00:00+09:00",
            "original_end": "2024-01-15T15:00:00+09:00",
            "attendees": ["a@test.com", "b@test.com"],
            "duration_minutes": 60,
            "candidates": [
                {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},
                {"start": "2024-01-15T11:00:00+09:00", "end": "2024-01-15T12:00:00+09:00"},
            ],
            "fallback_used": False,
        }
        blocks = build_reschedule_suggestion_blocks(result_data)

        # Header + info + divider + 2 candidates = 5
        assert len(blocks) == 5
        assert blocks[0]["type"] == "header"
        assert "リスケジュール候補" in blocks[0]["text"]["text"]
        assert blocks[2]["type"] == "divider"

    def test_fallback_context_shown(self):
        result_data = {
            "event_id": "event123",
            "summary": "MTG",
            "original_start": "2024-01-15T14:00:00+09:00",
            "original_end": "2024-01-15T15:00:00+09:00",
            "attendees": ["a@test.com"],
            "duration_minutes": 60,
            "candidates": [
                {"start": "2024-01-16T10:00:00+09:00", "end": "2024-01-16T11:00:00+09:00"},
            ],
            "fallback_used": True,
        }
        blocks = build_reschedule_suggestion_blocks(result_data)

        # Header + info + divider + context + 1 candidate = 5
        assert len(blocks) == 5
        context_block = blocks[3]
        assert context_block["type"] == "context"
        assert "翌営業日" in context_block["elements"][0]["text"]

    def test_button_action_data(self):
        result_data = {
            "event_id": "event123",
            "summary": "MTG",
            "original_start": "2024-01-15T14:00:00+09:00",
            "original_end": "2024-01-15T15:00:00+09:00",
            "attendees": ["a@test.com"],
            "duration_minutes": 60,
            "candidates": [
                {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},
            ],
            "fallback_used": False,
        }
        blocks = build_reschedule_suggestion_blocks(result_data)

        button_block = blocks[3]
        action_value = json.loads(button_block["accessory"]["value"])
        assert action_value["action"] == "confirm_reschedule"
        assert action_value["event_id"] == "event123"
        assert button_block["accessory"]["action_id"] == "confirm_reschedule_0"

    def test_empty_candidates(self):
        result_data = {
            "event_id": "event123",
            "summary": "MTG",
            "attendees": ["a@test.com"],
            "duration_minutes": 60,
            "candidates": [],
            "fallback_used": False,
        }
        blocks = build_reschedule_suggestion_blocks(result_data)
        # Header + info + divider = 3
        assert len(blocks) == 3


class TestBuildEventCreatedBlocks:
    def test_basic_structure(self):
        event_data = {
            "summary": "テストMTG",
            "start": "2024-01-15T14:00:00+09:00",
            "end": "2024-01-15T14:30:00+09:00",
            "attendees": ["a@test.com"],
            "html_link": "https://calendar.google.com/event/123",
        }
        blocks = build_event_created_blocks(event_data)

        assert len(blocks) == 3
        assert blocks[0]["type"] == "header"

    def test_without_link(self):
        event_data = {
            "summary": "テストMTG",
            "start": "2024-01-15T14:00:00+09:00",
            "end": "2024-01-15T14:30:00+09:00",
            "attendees": [],
        }
        blocks = build_event_created_blocks(event_data)
        assert len(blocks) == 2


class TestBuildOAuthPromptBlocks:
    def test_structure(self):
        blocks = build_oauth_prompt_blocks("https://accounts.google.com/o/oauth2/auth?...")

        assert len(blocks) == 1
        assert blocks[0]["type"] == "section"
        assert blocks[0]["accessory"]["type"] == "button"
        assert "google.com" in blocks[0]["accessory"]["url"]


class TestBuildSlotConfirmationModal:
    def test_basic_structure(self):
        slot_data = {
            "start": "2024-01-15T14:00:00+09:00",
            "end": "2024-01-15T14:30:00+09:00",
            "attendees": ["a@test.com"],
            "summary": "テストMTG",
        }
        modal = build_slot_confirmation_modal(slot_data, "C123", "1234.5678")

        assert modal["type"] == "modal"
        assert modal["callback_id"] == "slot_confirmation_modal"
        assert modal["submit"]["text"] == "予約する"
        assert modal["close"]["text"] == "キャンセル"
        assert len(modal["blocks"]) == 3

    def test_initial_value_has_summary(self):
        slot_data = {
            "start": "2024-01-15T14:00:00+09:00",
            "end": "2024-01-15T14:30:00+09:00",
            "attendees": ["a@test.com"],
            "summary": "企画会議",
        }
        modal = build_slot_confirmation_modal(slot_data, "C123", "1234.5678")

        input_block = modal["blocks"][0]
        assert input_block["type"] == "input"
        assert input_block["block_id"] == "summary_block"
        assert input_block["element"]["action_id"] == "summary_input"
        assert input_block["element"]["initial_value"] == "企画会議"

    def test_private_metadata_contains_required_fields(self):
        slot_data = {
            "start": "2024-01-15T14:00:00+09:00",
            "end": "2024-01-15T14:30:00+09:00",
            "attendees": ["a@test.com", "b@test.com"],
            "summary": "MTG",
        }
        modal = build_slot_confirmation_modal(slot_data, "C999", "9999.1234")

        metadata = json.loads(modal["private_metadata"])
        assert metadata["channel_id"] == "C999"
        assert metadata["message_ts"] == "9999.1234"
        assert metadata["start"] == "2024-01-15T14:00:00+09:00"
        assert metadata["end"] == "2024-01-15T14:30:00+09:00"
        assert metadata["attendees"] == ["a@test.com", "b@test.com"]

    def test_time_and_attendees_display(self):
        slot_data = {
            "start": "2024-01-15T14:00:00+09:00",
            "end": "2024-01-15T14:30:00+09:00",
            "attendees": ["a@test.com"],
            "summary": "MTG",
        }
        modal = build_slot_confirmation_modal(slot_data, "C123", "1234.5678")

        time_block = modal["blocks"][1]
        assert "📅" in time_block["text"]["text"]
        assert "01/15 14:00 - 14:30" in time_block["text"]["text"]

        attendees_block = modal["blocks"][2]
        assert "👥" in attendees_block["text"]["text"]
        assert "a@test.com" in attendees_block["text"]["text"]


class TestResolveUserMentions:
    def test_replaces_mention_with_email(self):
        client = MagicMock()
        client.users_info.return_value = {
            "user": {"profile": {"email": "tanaka@example.com"}}
        }
        result = resolve_user_mentions("<@U12345> の予定を教えて", client)
        assert result == "tanaka@example.com の予定を教えて"
        client.users_info.assert_called_once_with(user="U12345")

    def test_multiple_mentions(self):
        client = MagicMock()
        client.users_info.side_effect = [
            {"user": {"profile": {"email": "a@example.com"}}},
            {"user": {"profile": {"email": "b@example.com"}}},
        ]
        result = resolve_user_mentions("<@U111> と <@U222> のMTG", client)
        assert "a@example.com" in result
        assert "b@example.com" in result

    def test_no_mentions(self):
        client = MagicMock()
        result = resolve_user_mentions("予定を教えて", client)
        assert result == "予定を教えて"
        client.users_info.assert_not_called()

    def test_no_email_keeps_mention(self):
        client = MagicMock()
        client.users_info.return_value = {
            "user": {"profile": {}}
        }
        result = resolve_user_mentions("<@U12345> の予定", client)
        assert "<@U12345>" in result

    def test_api_error_keeps_mention(self):
        client = MagicMock()
        client.users_info.side_effect = Exception("API error")
        result = resolve_user_mentions("<@U12345> の予定", client)
        assert "<@U12345>" in result
