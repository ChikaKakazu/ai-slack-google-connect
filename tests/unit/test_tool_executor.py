"""Tests for tool_executor module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.tool_executor import ToolExecutor


@pytest.fixture
def executor():
    return ToolExecutor()


class TestToolExecutor:
    @patch("tools.tool_executor.token_service")
    def test_no_credentials_returns_oauth_required(self, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = None

        result = executor.execute("search_free_slots", {"attendees": [], "date": "明日"}, "U123")
        data = json.loads(result)

        assert data["action"] == "oauth_required"

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_search_free_slots(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.search_free_slots.return_value = [
            {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"},
        ]

        result = executor.execute(
            "search_free_slots",
            {"attendees": ["a@test.com"], "date": "2024-01-15"},
            "U123",
        )
        data = json.loads(result)

        assert data["total_slots"] == 1
        assert len(data["slots"]) == 1

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_create_event(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.create_event.return_value = {
            "id": "event123",
            "htmlLink": "https://calendar.google.com/event/123",
            "summary": "テストMTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T14:30:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }

        result = executor.execute(
            "create_event",
            {
                "summary": "テストMTG",
                "start_time": "2024-01-15T14:00:00+09:00",
                "end_time": "2024-01-15T14:30:00+09:00",
                "attendees": ["a@test.com"],
            },
            "U123",
        )
        data = json.loads(result)

        assert data["status"] == "created"
        assert data["event_id"] == "event123"

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_unknown_tool(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()

        result = executor.execute("nonexistent_tool", {}, "U123")
        data = json.loads(result)

        assert "error" in data
        assert "Unknown tool" in data["error"]
