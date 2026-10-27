from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta
import re
import unicodedata
from zoneinfo import ZoneInfo


WEEKDAYS = {
    "mo": 0, "montag": 0,
    "di": 1, "dienstag": 1,
    "mi": 2, "mittwoch": 2,
    "do": 3, "donnerstag": 3,
    "fr": 4, "freitag": 4,
    "sa": 5, "samstag": 5,
    "so": 6, "sonntag": 6,
}
DAY = r"(?P<day>montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|mo|di|mi|do|fr|sa|so)\.?"
DATE = r"(?P<date>\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)"
VALUE = r"(?P<value>frei|urlaub|(?:[01]?\d|2[0-3])(?:(?::|\.)?[0-5]\d)?(?:\s*uhr)?)"
ITEM = re.compile(rf"(?:{DAY}|{DATE})\s*(?:[-:=]\s*)?{VALUE}", re.IGNORECASE)


@dataclass(frozen=True)
class ScheduleEntry:
    date: str
    start: str | None
    free: bool
    source: str = "whatsapp"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class ParseError(ValueError):
    pass


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"[\t ]+", " ", normalized).strip()


def _next_weekday(target: int, now: datetime, parsed_time: time | None) -> date:
    days = (target - now.weekday()) % 7
    candidate = now.date() + timedelta(days=days)
    if days == 0 and parsed_time is not None and datetime.combine(candidate, parsed_time, now.tzinfo) <= now:
        candidate += timedelta(days=7)
    return candidate


def _parse_date(raw: str, today: date) -> date:
    parts = [int(p) for p in re.split(r"[./-]", raw)]
    year = parts[2] if len(parts) == 3 else today.year
    if year < 100:
        year += 2000
    candidate = date(year, parts[1], parts[0])
    if len(parts) == 2 and candidate < today - timedelta(days=1):
        candidate = candidate.replace(year=year + 1)
    return candidate


def _parse_value(raw: str) -> tuple[str | None, bool, time | None]:
    raw = raw.strip().replace("uhr", "").strip()
    if raw in {"frei", "urlaub"}:
        return None, True, None
    compact = raw.replace(".", ":")
    if ":" in compact:
        hour_s, minute_s = compact.split(":", 1)
    elif len(compact) in {3, 4}:
        hour_s, minute_s = compact[:-2], compact[-2:]
    else:
        hour_s, minute_s = compact, "00"
    hour, minute = int(hour_s), int(minute_s)
    parsed = time(hour=hour, minute=minute)
    return f"{hour:02d}:{minute:02d}", False, parsed


def parse_schedule(text: str, *, now: datetime | None = None, timezone: str = "Europe/Berlin") -> list[ScheduleEntry]:
    zone = ZoneInfo(timezone)
    now = now.astimezone(zone) if now else datetime.now(zone)
    source = _plain(text)
    found: dict[str, ScheduleEntry] = {}
    for match in ITEM.finditer(source):
        start, free, parsed_time = _parse_value(match.group("value"))
        if match.group("day"):
            day_key = match.group("day").rstrip(".")
            target_date = _next_weekday(WEEKDAYS[day_key], now, parsed_time)
        else:
            target_date = _parse_date(match.group("date"), now.date())
        found[target_date.isoformat()] = ScheduleEntry(
            date=target_date.isoformat(), start=start, free=free
        )
    if not found:
        raise ParseError(
            "Keine eindeutige Arbeitszeit erkannt. Beispiele: 'Di 05:30', '27.10 13:00' oder 'Fr frei'."
        )
    return sorted(found.values(), key=lambda item: item.date)
