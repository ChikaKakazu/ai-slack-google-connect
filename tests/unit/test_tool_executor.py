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
        mock_cal.search_free_slots.return_value = (
            [{"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"}],
            [{"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"}],
        )

        result = executor.execute(
            "search_free_slots",
            {"attendees": ["a@test.com"], "date": "2024-01-15"},
            "U123",
        )
        data = json.loads(result)

        assert data["total_slots"] == 1
        assert len(data["slots"]) == 1
        assert data["status"] == "suggest_schedule"
        assert data["summary"] == "ミーティング"

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_search_free_slots_with_summary(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal
        mock_cal.search_free_slots.return_value = (
            [{"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T14:30:00+09:00"}],
            [],
        )

        result = executor.execute(
            "search_free_slots",
            {"attendees": ["a@test.com"], "date": "2024-01-15", "summary": "企画会議"},
            "U123",
        )
        data = json.loads(result)

        assert data["status"] == "suggest_schedule"
        assert data["summary"] == "企画会議"

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

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_search_free_slots_non_business_day_warning(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()

        # 2024-01-13 is Saturday
        result = executor.execute(
            "search_free_slots",
            {"attendees": ["a@test.com"], "date": "2024-01-13"},
            "U123",
        )
        data = json.loads(result)

        assert "warning" in data
        assert "営業日外" in data["warning"]
        assert data["total_slots"] == 0
        assert data["status"] == "suggest_schedule"


class TestSuggestReschedule:
    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_returns_candidates(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "定例MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}, {"email": "b@test.com"}],
        }
        mock_cal.search_free_slots.return_value = (
            [
                {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},
                {"start": "2024-01-15T11:00:00+09:00", "end": "2024-01-15T12:00:00+09:00"},
                {"start": "2024-01-15T13:00:00+09:00", "end": "2024-01-15T14:00:00+09:00"},
                {"start": "2024-01-15T16:00:00+09:00", "end": "2024-01-15T17:00:00+09:00"},
            ],
            [],
        )

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        assert data["status"] == "suggest_reschedule"
        assert len(data["candidates"]) == 3  # Max 3
        assert data["summary"] == "定例MTG"
        assert data["duration_minutes"] == 60
        assert data["attendees"] == ["a@test.com", "b@test.com"]

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_no_attendees_falls_back_to_organizer(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "個人作業",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [],
            "organizer": {"email": "me@example.com"},
        }
        mock_cal.search_free_slots.return_value = (
            [{"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"}],
            [],
        )

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        assert data["status"] == "suggest_reschedule"
        assert data["attendees"] == ["me@example.com"]

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_no_attendees_no_organizer_returns_error(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "個人作業",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [],
        }

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        assert "error" in data

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_no_slots_fallback_to_next_business_day(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }
        # First call: no slots, second call: has slots
        mock_cal.search_free_slots.side_effect = [
            ([], []),
            ([{"start": "2024-01-16T10:00:00+09:00", "end": "2024-01-16T11:00:00+09:00"}], []),
        ]

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        assert data["status"] == "suggest_reschedule"
        assert data["fallback_used"] is True
        assert len(data["candidates"]) == 1

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_no_slots_at_all(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }
        mock_cal.search_free_slots.return_value = ([], [])

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        assert data["status"] == "suggest_reschedule"
        assert data["no_slots_found"] is True

    @patch("tools.tool_executor.now_jst")
    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_today_filters_past_slots(self, mock_cal_cls, mock_token_service, mock_now, executor):
        from datetime import datetime
        from utils.time_utils import JST

        mock_now.return_value = datetime(2024, 1, 15, 15, 0, 0, tzinfo=JST)
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }
        # Return slots including past ones - full day search
        mock_cal.search_free_slots.return_value = (
            [
                {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},  # past
                {"start": "2024-01-15T16:00:00+09:00", "end": "2024-01-15T17:00:00+09:00"},  # future
                {"start": "2024-01-15T17:00:00+09:00", "end": "2024-01-15T18:00:00+09:00"},  # future
                {"start": "2024-01-15T18:00:00+09:00", "end": "2024-01-15T19:00:00+09:00"},  # future
            ],
            [],
        )

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        # Past slot (10:00) should be filtered out
        assert len(data["candidates"]) == 3
        assert data["candidates"][0]["start"] == "2024-01-15T16:00:00+09:00"

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_same_day_priority_then_next_day(self, mock_cal_cls, mock_token_service, executor):
        """Same-day slots should come first, then next business day fills remaining."""
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }
        # Same day has 2 slots (< 3), next day has more
        mock_cal.search_free_slots.side_effect = [
            (
                [
                    {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},
                    {"start": "2024-01-15T16:00:00+09:00", "end": "2024-01-15T17:00:00+09:00"},
                ],
                [],
            ),
            (
                [
                    {"start": "2024-01-16T10:00:00+09:00", "end": "2024-01-16T11:00:00+09:00"},
                    {"start": "2024-01-16T11:00:00+09:00", "end": "2024-01-16T12:00:00+09:00"},
                ],
                [],
            ),
        ]

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        assert len(data["candidates"]) == 3
        # First 2 should be from same day (Jan 15)
        assert "2024-01-15" in data["candidates"][0]["start"]
        assert "2024-01-15" in data["candidates"][1]["start"]
        # 3rd from next day (Jan 16)
        assert "2024-01-16" in data["candidates"][2]["start"]

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_excludes_original_event_time(self, mock_cal_cls, mock_token_service, executor):
        """Original event time should not appear as a candidate."""
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.get_event.return_value = {
            "id": "event123",
            "summary": "MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }
        mock_cal.search_free_slots.return_value = (
            [
                {"start": "2024-01-15T14:00:00+09:00", "end": "2024-01-15T15:00:00+09:00"},  # same as original
                {"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"},
                {"start": "2024-01-15T16:00:00+09:00", "end": "2024-01-15T17:00:00+09:00"},
                {"start": "2024-01-15T17:00:00+09:00", "end": "2024-01-15T18:00:00+09:00"},
            ],
            [],
        )

        result = executor.execute("suggest_reschedule", {"event_id": "event123"}, "U123")
        data = json.loads(result)

        # Original time (14:00-15:00) should be excluded
        for c in data["candidates"]:
            assert c["start"] != "2024-01-15T14:00:00+09:00"
        assert len(data["candidates"]) == 3

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_search_by_event_title(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.search_events.return_value = [
            {
                "id": "found_event",
                "summary": "MTG被りテスト",
                "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
                "end": {"dateTime": "2024-01-15T15:00:00+09:00"},
                "attendees": [{"email": "a@test.com"}],
            }
        ]
        mock_cal.search_free_slots.return_value = (
            [{"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"}],
            [],
        )

        result = executor.execute("suggest_reschedule", {"event_title": "MTG被りテスト"}, "U123")
        data = json.loads(result)

        assert data["status"] == "suggest_reschedule"
        assert data["event_id"] == "found_event"
        assert data["summary"] == "MTG被りテスト"
        mock_cal.search_events.assert_called_once_with("MTG被りテスト")

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_event_title_not_found(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()
        mock_cal = MagicMock()
        mock_cal_cls.return_value = mock_cal

        mock_cal.search_events.return_value = []

        result = executor.execute("suggest_reschedule", {"event_title": "存在しないMTG"}, "U123")
        data = json.loads(result)

        assert "error" in data
        assert "見つかりませんでした" in data["error"]

    @patch("tools.tool_executor.token_service")
    @patch("tools.tool_executor.CalendarService")
    def test_no_event_id_or_title_returns_error(self, mock_cal_cls, mock_token_service, executor):
        mock_token_service.get_credentials.return_value = MagicMock()

        result = executor.execute("suggest_reschedule", {}, "U123")
        data = json.loads(result)

        assert "error" in data
        assert "event_id" in data["error"]
