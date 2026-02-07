"""Timezone and datetime utilities."""

from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    """Return current datetime in JST."""
    return datetime.now(JST)


def to_rfc3339(dt: datetime) -> str:
    """Convert datetime to RFC3339 format string for Google Calendar API."""
    return dt.isoformat()


def parse_datetime(dt_str: str) -> datetime:
    """Parse a datetime string, assuming JST if no timezone info.

    Supports formats:
        - 2024-01-15T14:00:00+09:00 (ISO with tz)
        - 2024-01-15T14:00:00 (ISO without tz, assumes JST)
        - 2024-01-15 14:00 (simple format, assumes JST)
    """
    dt_str = dt_str.strip()

    # Try ISO format
    try:
        dt = datetime.fromisoformat(dt_str)
        # If no timezone info, assume JST
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        return dt
    except ValueError:
        pass

    # Try simple format
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            return dt.replace(tzinfo=JST)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse datetime: {dt_str}")


def get_date_range(date_str: str) -> tuple[datetime, datetime]:
    """Get start and end of a date for FreeBusy queries.

    Args:
        date_str: Date string like '2024-01-15' or 'tomorrow'.

    Returns:
        Tuple of (start_of_day, end_of_day) in JST.
    """
    today = now_jst().date()

    if date_str.lower() in ("today", "今日"):
        target = today
    elif date_str.lower() in ("tomorrow", "明日"):
        target = today + timedelta(days=1)
    elif date_str.lower() in ("day after tomorrow", "明後日"):
        target = today + timedelta(days=2)
    else:
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Unable to parse date: {date_str}")

    start = datetime(target.year, target.month, target.day, 0, 0, 0, tzinfo=JST)
    end = start + timedelta(days=1)
    return start, end


def find_free_slots(
    busy_periods: list[dict],
    range_start: datetime,
    range_end: datetime,
    duration_minutes: int = 30,
    work_start_hour: int = 9,
    work_end_hour: int = 18,
) -> list[dict]:
    """Find available time slots within a range, excluding busy periods.

    Args:
        busy_periods: List of {"start": datetime, "end": datetime} dicts.
        range_start: Start of search range.
        range_end: End of search range.
        duration_minutes: Required meeting duration in minutes.
        work_start_hour: Start of work hours (default 9).
        work_end_hour: End of work hours (default 18).

    Returns:
        List of {"start": str, "end": str} dicts in RFC3339 format.
    """
    # Clamp to work hours
    day_start = range_start.replace(hour=work_start_hour, minute=0, second=0)
    day_end = range_start.replace(hour=work_end_hour, minute=0, second=0)

    if range_start > day_start:
        day_start = range_start
    if range_end < day_end:
        day_end = range_end

    if day_start >= day_end:
        return []

    # Sort busy periods
    sorted_busy = sorted(busy_periods, key=lambda x: x["start"])

    # Find gaps
    slots = []
    current = day_start
    duration = timedelta(minutes=duration_minutes)

    for busy in sorted_busy:
        busy_start = busy["start"] if isinstance(busy["start"], datetime) else parse_datetime(busy["start"])
        busy_end = busy["end"] if isinstance(busy["end"], datetime) else parse_datetime(busy["end"])

        # If there's a gap before this busy period
        if current + duration <= busy_start:
            # Generate slots in this gap
            slot_start = current
            while slot_start + duration <= busy_start and slot_start + duration <= day_end:
                slots.append({
                    "start": to_rfc3339(slot_start),
                    "end": to_rfc3339(slot_start + duration),
                })
                slot_start += timedelta(minutes=30)  # 30-min increments

        # Move past this busy period
        if busy_end > current:
            current = busy_end

    # Check remaining time after last busy period
    slot_start = current
    while slot_start + duration <= day_end:
        slots.append({
            "start": to_rfc3339(slot_start),
            "end": to_rfc3339(slot_start + duration),
        })
        slot_start += timedelta(minutes=30)

    return slots
