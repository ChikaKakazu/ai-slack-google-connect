"""Tests for calendar_service module."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from services.calendar_service import CalendarService
from utils.time_utils import JST


@pytest.fixture
def calendar_service():
    mock_creds = MagicMock()
    service = CalendarService(mock_creds)
    service.service = MagicMock()
    return service


class TestGetFreebusy:
    def test_queries_multiple_calendars(self, calendar_service):
        calendar_service.service.freebusy().query().execute.return_value = {
            "calendars": {
                "a@test.com": {"busy": [{"start": "2024-01-15T10:00:00+09:00", "end": "2024-01-15T11:00:00+09:00"}]},
                "b@test.com": {"busy": []},
            }
        }

        result = calendar_service.get_freebusy(
            calendar_ids=["a@test.com", "b@test.com"],
            time_min=datetime(2024, 1, 15, 9, 0, tzinfo=JST),
            time_max=datetime(2024, 1, 15, 18, 0, tzinfo=JST),
        )

        assert len(result["a@test.com"]) == 1
        assert len(result["b@test.com"]) == 0


class TestSearchFreeSlots:
    def test_finds_slots(self, calendar_service):
        calendar_service.service.freebusy().query().execute.return_value = {
            "calendars": {
                "a@test.com": {"busy": [{"start": "2024-01-15T09:00:00+09:00", "end": "2024-01-15T10:00:00+09:00"}]},
            }
        }

        slots = calendar_service.search_free_slots(
            calendar_ids=["a@test.com"],
            time_min=datetime(2024, 1, 15, 0, 0, tzinfo=JST),
            time_max=datetime(2024, 1, 16, 0, 0, tzinfo=JST),
            duration_minutes=30,
        )

        assert len(slots) > 0
        # First slot should be after 10:00
        assert "T10:00:00" in slots[0]["start"]


class TestCreateEvent:
    def test_creates_event(self, calendar_service):
        expected_event = {
            "id": "event123",
            "htmlLink": "https://calendar.google.com/event/123",
            "summary": "Test MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T14:30:00+09:00"},
            "attendees": [{"email": "a@test.com"}],
        }
        calendar_service.service.events().insert().execute.return_value = expected_event

        result = calendar_service.create_event(
            summary="Test MTG",
            start_time=datetime(2024, 1, 15, 14, 0, tzinfo=JST),
            end_time=datetime(2024, 1, 15, 14, 30, tzinfo=JST),
            attendees=["a@test.com"],
        )

        assert result["id"] == "event123"

    def test_creates_event_with_description(self, calendar_service):
        calendar_service.service.events().insert().execute.return_value = {"id": "e1", "summary": "MTG"}

        calendar_service.create_event(
            summary="MTG",
            start_time=datetime(2024, 1, 15, 14, 0, tzinfo=JST),
            end_time=datetime(2024, 1, 15, 14, 30, tzinfo=JST),
            attendees=["a@test.com"],
            description="Important meeting",
        )

        call_kwargs = calendar_service.service.events().insert.call_args
        body = call_kwargs[1]["body"] if "body" in (call_kwargs[1] if call_kwargs[1] else {}) else None
        # Just verify it doesn't raise


class TestRescheduleEvent:
    def test_reschedules_event(self, calendar_service):
        calendar_service.service.events().get().execute.return_value = {
            "id": "event123",
            "summary": "Original MTG",
            "start": {"dateTime": "2024-01-15T14:00:00+09:00"},
            "end": {"dateTime": "2024-01-15T14:30:00+09:00"},
        }
        calendar_service.service.events().update().execute.return_value = {
            "id": "event123",
            "summary": "Original MTG",
            "start": {"dateTime": "2024-01-16T10:00:00+09:00"},
            "end": {"dateTime": "2024-01-16T10:30:00+09:00"},
        }

        result = calendar_service.reschedule_event(
            event_id="event123",
            new_start=datetime(2024, 1, 16, 10, 0, tzinfo=JST),
            new_end=datetime(2024, 1, 16, 10, 30, tzinfo=JST),
        )

        assert result["id"] == "event123"
