"""Tests for slack_utils module."""

import json

from utils.slack_utils import (
    build_event_created_blocks,
    build_free_slots_blocks,
    build_oauth_prompt_blocks,
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
