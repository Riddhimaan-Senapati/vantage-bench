"""
calendar_availability.py
========================
Reads an ICS calendar file and calculates how available a person is
during working hours for a given date range.

Usage (CLI):
    python calendar_availability.py
    python calendar_availability.py --ics dummy_maya_calendar.ics --start 2026-02-23 --end 2026-02-28
    python calendar_availability.py --ics dummy_maya_calendar.ics --start 2026-03-02 --end 2026-03-07

Dependencies:
    pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events


# ── Configuration ─────────────────────────────────────────────────────────────

WORK_START: time = time(9, 0)    # 09:00
WORK_END:   time = time(18, 0)   # 18:00
WORK_DAYS:  set[int] = {0, 1, 2, 3, 4}  # Monday=0 … Friday=4
WORK_MINUTES_PER_DAY: int = (
    int((datetime.combine(date.today(), WORK_END) - datetime.combine(date.today(), WORK_START))
        .total_seconds() / 60)
)  # = 540 for 09:00–18:00


# ── Interval helpers ──────────────────────────────────────────────────────────

Interval = tuple[datetime, datetime]


def merge_intervals(intervals: list[Interval]) -> list[Interval]:
    """Merge overlapping or adjacent (start, end) datetime intervals."""
    if not intervals:
        return []
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged: list[Interval] = [sorted_ivs[0]]
    for start, end in sorted_ivs[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def clip_to_window(
    start: datetime,
    end: datetime,
    window_start: datetime,
    window_end: datetime,
) -> Interval | None:
    """Clip an interval to a window. Returns None when they don't overlap."""
    clipped_start = max(start, window_start)
    clipped_end   = min(end,   window_end)
    if clipped_start >= clipped_end:
        return None
    return clipped_start, clipped_end


def interval_minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() / 60)


# ── Calendar loading ──────────────────────────────────────────────────────────

def load_calendar(ics_path: str | Path) -> icalendar.Calendar:
    """Read and parse an ICS file into an icalendar.Calendar object."""
    path = Path(ics_path)
    if not path.exists():
        raise FileNotFoundError(f"ICS file not found: {path.resolve()}")
    return icalendar.Calendar.from_ical(path.read_bytes())


def _to_aware_datetime(dt: date | datetime, tz: ZoneInfo) -> datetime:
    """Normalise a `date` or naive `datetime` to a timezone-aware `datetime`."""
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=tz)
    # All-day event — treat as the very start of that day in the given tz
    return datetime(dt.year, dt.month, dt.day, tzinfo=tz)


def _is_transparent(event: icalendar.Event) -> bool:
    """
    Events marked TRANSP:TRANSPARENT don't block time (e.g., reminders,
    tentative appointments where the person is still reachable).
    """
    transp = event.get("TRANSP", "OPAQUE")
    return str(transp).upper() == "TRANSPARENT"


def _is_allday(event: icalendar.Event) -> bool:
    """Return True if the DTSTART is a plain date (not a datetime)."""
    dtstart = event.get("DTSTART")
    if dtstart is None:
        return False
    return isinstance(dtstart.dt, date) and not isinstance(dtstart.dt, datetime)


def get_busy_intervals(
    cal: icalendar.Calendar,
    range_start: date,
    range_end: date,
    tz: ZoneInfo,
) -> list[Interval]:
    """
    Expand all events (including RRULE recurrences) that fall within
    [range_start, range_end) and return their (start, end) datetime pairs.

    Rules applied:
    - TRANSP:TRANSPARENT events are skipped (they don't block availability).
    - All-day events spanning a working day count as a full-day block.
    - Events outside working hours are still returned here; clipping happens
      later in `calculate_availability` so we have full event data for logging.
    """
    events = recurring_ical_events.of(cal).between(range_start, range_end)
    intervals: list[Interval] = []

    for event in events:
        if _is_transparent(event):
            continue

        raw_start = event.get("DTSTART")
        raw_end   = event.get("DTEND")

        if raw_start is None:
            continue

        if _is_allday(event):
            # All-day event — block the entire working day
            day = raw_start.dt
            dt_start = datetime.combine(day, WORK_START, tzinfo=tz)
            dt_end   = datetime.combine(day, WORK_END,   tzinfo=tz)
        else:
            dt_start = _to_aware_datetime(raw_start.dt, tz)
            dt_end = (
                _to_aware_datetime(raw_end.dt, tz)
                if raw_end is not None
                else dt_start + timedelta(hours=1)
            )

        if dt_end > dt_start:
            intervals.append((dt_start, dt_end))

    return intervals


# ── Availability calculation ──────────────────────────────────────────────────

def calculate_availability(
    busy_intervals: list[Interval],
    range_start: date,
    range_end: date,
    tz: ZoneInfo,
    work_start: time = WORK_START,
    work_end: time = WORK_END,
    work_days: set[int] = WORK_DAYS,
) -> dict:
    """
    Calculate availability % for each working day and overall.

    For each working day:
      1. Clip every busy interval to the 09:00–18:00 window.
      2. Merge overlapping clipped intervals.
      3. availability_pct = (work_minutes - busy_minutes) / work_minutes * 100

    Returns a structured dict with per-day detail and an overall summary.
    """
    total_work_minutes      = 0
    total_busy_minutes      = 0
    per_day: list[dict]     = []

    current = range_start
    while current < range_end:
        if current.weekday() not in work_days:
            current += timedelta(days=1)
            continue

        window_start = datetime.combine(current, work_start, tzinfo=tz)
        window_end   = datetime.combine(current, work_end,   tzinfo=tz)
        work_min     = interval_minutes(window_start, window_end)

        # Clip every interval to this day's working window
        clipped: list[Interval] = []
        for iv_start, iv_end in busy_intervals:
            c = clip_to_window(iv_start, iv_end, window_start, window_end)
            if c:
                clipped.append(c)

        merged      = merge_intervals(clipped)
        busy_min    = sum(interval_minutes(s, e) for s, e in merged)
        avail_min   = work_min - busy_min
        avail_pct   = round(avail_min / work_min * 100, 1)

        per_day.append({
            "date":              current.isoformat(),
            "weekday":           current.strftime("%A"),
            "work_minutes":      work_min,
            "busy_minutes":      busy_min,
            "available_minutes": avail_min,
            "availability_pct":  avail_pct,
            "blocked_blocks": [
                {
                    "start":        s.strftime("%H:%M"),
                    "end":          e.strftime("%H:%M"),
                    "duration_min": interval_minutes(s, e),
                }
                for s, e in merged
            ],
        })

        total_work_minutes += work_min
        total_busy_minutes += busy_min
        current += timedelta(days=1)

    overall_avail_min = total_work_minutes - total_busy_minutes
    overall_pct = (
        round(overall_avail_min / total_work_minutes * 100, 1)
        if total_work_minutes > 0
        else 100.0
    )

    return {
        "total_work_minutes":      total_work_minutes,
        "total_busy_minutes":      total_busy_minutes,
        "total_available_minutes": overall_avail_min,
        "availability_pct":        overall_pct,
        "per_day":                 per_day,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def get_availability_report(
    ics_path: str | Path,
    range_start: date | None = None,
    range_end:   date | None = None,
    timezone:    str = "UTC",
) -> dict:
    """
    Full pipeline: load ICS → expand events → calculate availability.

    Args:
        ics_path:    Path to the .ics file.
        range_start: First day of the range (inclusive). Defaults to today.
        range_end:   Last day of the range (exclusive). Defaults to +7 days.
        timezone:    IANA timezone string, e.g. "Europe/Paris" or "America/New_York".

    Returns:
        A dict containing:
            ics_file          – resolved path to the ICS
            timezone          – timezone used
            range_start/end   – ISO date strings
            availability_pct  – float 0–100 (overall)
            total_*_minutes   – integer summaries
            per_day           – list of per-day breakdowns
            generated_at      – ISO timestamp of when this ran
    """
    tz    = ZoneInfo(timezone)
    today = date.today()
    start = range_start or today
    end   = range_end   or (today + timedelta(weeks=1))

    cal   = load_calendar(ics_path)
    busy  = get_busy_intervals(cal, start, end, tz=tz)
    stats = calculate_availability(busy, start, end, tz=tz)

    return {
        "ics_file":     str(Path(ics_path).resolve()),
        "timezone":     timezone,
        "range_start":  start.isoformat(),
        "range_end":    end.isoformat(),
        "generated_at": datetime.now(tz=tz).isoformat(),
        **stats,
    }


# ── Pretty-print helpers ──────────────────────────────────────────────────────

def _bar(pct: float, width: int = 30) -> str:
    """Render a simple ASCII progress bar."""
    filled = round(pct / 100 * width)
    return f"[{'#' * filled}{'-' * (width - filled)}] {pct:5.1f}%"


def print_report(report: dict) -> None:
    """Print a human-readable availability report to stdout."""
    sep = "-" * 60
    print(sep)
    print(f"  CoverageIQ - Calendar Availability Report")
    print(sep)
    print(f"  ICS file   : {report['ics_file']}")
    print(f"  Range      : {report['range_start']} to {report['range_end']}")
    print(f"  Timezone   : {report['timezone']}")
    print(f"  Generated  : {report['generated_at']}")
    print(sep)

    for day in report["per_day"]:
        pct   = day["availability_pct"]
        label = f"  {day['weekday'][:3]} {day['date']}  "
        print(f"{label}{_bar(pct)}  ({day['available_minutes']} / {day['work_minutes']} min free)")
        for block in day["blocked_blocks"]:
            print(f"      * {block['start']}-{block['end']}  ({block['duration_min']} min)")

    print(sep)
    overall = report["availability_pct"]
    print(f"  OVERALL    {_bar(overall)}")
    print(
        f"             {report['total_available_minutes']} / "
        f"{report['total_work_minutes']} min available across "
        f"{len(report['per_day'])} working days"
    )
    print(sep)


# ── CLI entry point ───────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    here = Path(__file__).parent
    parser = argparse.ArgumentParser(
        description="Calculate person availability from an ICS calendar file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ics",
        default=str(here / "dummy_maya_calendar.ics"),
        help="Path to the .ics file.",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Range start date YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Range end date YYYY-MM-DD, exclusive (default: today + 7 days).",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone name, e.g. Europe/Paris.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of the formatted report.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    start = date.fromisoformat(args.start) if args.start else None
    end   = date.fromisoformat(args.end)   if args.end   else None

    report = get_availability_report(
        ics_path    = args.ics,
        range_start = start,
        range_end   = end,
        timezone    = args.timezone,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
