from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.parser import ParseError, parse_schedule


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))


def test_multiple_weekdays_and_compact_time():
    entries = parse_schedule("Di 530, Mi 05:00; Fr 13 Uhr; Sa frei", now=NOW)
    assert [entry.as_dict() for entry in entries] == [
        {"date": "2026-10-27", "start": "05:30", "free": False, "source": "whatsapp"},
        {"date": "2026-10-28", "start": "05:00", "free": False, "source": "whatsapp"},
        {"date": "2026-10-30", "start": "13:00", "free": False, "source": "whatsapp"},
        {"date": "2026-10-31", "start": None, "free": True, "source": "whatsapp"},
    ]


def test_explicit_date_and_year_rollover():
    now = datetime(2026, 12, 30, 8, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    assert parse_schedule("02.01 07:15", now=now)[0].date == "2027-01-02"


def test_unambiguous_failure_keeps_old_schedule_safe():
    with pytest.raises(ParseError):
        parse_schedule("Komm morgen etwas früher", now=NOW)
