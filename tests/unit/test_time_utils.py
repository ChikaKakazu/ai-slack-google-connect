"""Tests for time_utils module."""

from datetime import datetime, timedelta, timezone

import pytest

from utils.time_utils import (
    JST,
    find_free_slots,
    get_date_range,
    parse_datetime,
    to_rfc3339,
)


class TestParseDateTime:
    def test_iso_with_timezone(self):
        result = parse_datetime("2024-01-15T14:00:00+09:00")
        assert result.hour == 14
        assert result.tzinfo is not None

    def test_iso_without_timezone_assumes_jst(self):
        result = parse_datetime("2024-01-15T14:00:00")
        assert result.hour == 14
        assert result.tzinfo == JST

    def test_simple_format(self):
        result = parse_datetime("2024-01-15 14:00")
        assert result.hour == 14
        assert result.minute == 0
        assert result.tzinfo == JST

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unable to parse"):
            parse_datetime("not-a-date")


class TestToRfc3339:
    def test_converts_datetime(self):
        dt = datetime(2024, 1, 15, 14, 0, 0, tzinfo=JST)
        result = to_rfc3339(dt)
        assert "2024-01-15T14:00:00" in result


class TestGetDateRange:
    def test_specific_date(self):
        start, end = get_date_range("2024-01-15")
        assert start.date().isoformat() == "2024-01-15"
        assert end.date().isoformat() == "2024-01-16"
        assert start.hour == 0
        assert end.hour == 0

    def test_today(self):
        start, end = get_date_range("今日")
        assert start.date() == datetime.now(JST).date()

    def test_tomorrow(self):
        start, end = get_date_range("明日")
        expected = datetime.now(JST).date() + timedelta(days=1)
        assert start.date() == expected

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError):
            get_date_range("invalid")


class TestFindFreeSlots:
    def test_no_busy_periods_returns_full_day(self):
        start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
        end = datetime(2024, 1, 16, 0, 0, 0, tzinfo=JST)

        slots = find_free_slots([], start, end, duration_minutes=30)
        assert len(slots) > 0
        # First slot should start at 9:00
        first = parse_datetime(slots[0]["start"])
        assert first.hour == 9
        assert first.minute == 0

    def test_fully_busy_returns_empty(self):
        start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
        end = datetime(2024, 1, 16, 0, 0, 0, tzinfo=JST)

        busy = [{
            "start": datetime(2024, 1, 15, 9, 0, 0, tzinfo=JST),
            "end": datetime(2024, 1, 15, 18, 0, 0, tzinfo=JST),
        }]

        slots = find_free_slots(busy, start, end, duration_minutes=30)
        assert len(slots) == 0

    def test_gap_between_meetings(self):
        start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
        end = datetime(2024, 1, 16, 0, 0, 0, tzinfo=JST)

        busy = [
            {
                "start": datetime(2024, 1, 15, 9, 0, 0, tzinfo=JST),
                "end": datetime(2024, 1, 15, 10, 0, 0, tzinfo=JST),
            },
            {
                "start": datetime(2024, 1, 15, 11, 0, 0, tzinfo=JST),
                "end": datetime(2024, 1, 15, 18, 0, 0, tzinfo=JST),
            },
        ]

        slots = find_free_slots(busy, start, end, duration_minutes=30)
        assert len(slots) > 0
        # Should find slots between 10:00-11:00
        first = parse_datetime(slots[0]["start"])
        assert first.hour == 10
        assert first.minute == 0

    def test_custom_work_hours(self):
        start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
        end = datetime(2024, 1, 16, 0, 0, 0, tzinfo=JST)

        slots = find_free_slots([], start, end, duration_minutes=60, work_start_hour=10, work_end_hour=12)
        # 10:00-11:00, 10:30-11:30, 11:00-12:00
        assert len(slots) == 3

    def test_duration_longer_than_slot(self):
        start = datetime(2024, 1, 15, 0, 0, 0, tzinfo=JST)
        end = datetime(2024, 1, 16, 0, 0, 0, tzinfo=JST)

        busy = [
            {
                "start": datetime(2024, 1, 15, 9, 0, 0, tzinfo=JST),
                "end": datetime(2024, 1, 15, 9, 45, 0, tzinfo=JST),
            },
            {
                "start": datetime(2024, 1, 15, 10, 0, 0, tzinfo=JST),
                "end": datetime(2024, 1, 15, 18, 0, 0, tzinfo=JST),
            },
        ]

        # 15-min gap can't fit 30-min meeting
        slots = find_free_slots(busy, start, end, duration_minutes=30)
        # No slot should start at 9:45 since 9:45+30=10:15 > 10:00
        for slot in slots:
            slot_start = parse_datetime(slot["start"])
            assert not (slot_start.hour == 9 and slot_start.minute == 45)
