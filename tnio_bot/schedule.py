"""Build the 3 week messages from calendar events. No network access.

See docs/SPEC.md for the rules (schedule week, late-night cutoff, overflow).
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from tnio_bot.config import EASTERN
from tnio_bot.hosts import host_text, mention_title_names, title_names

log = logging.getLogger(__name__)

LATE_NIGHT_CUTOFF = time(5)
POST_TIME = time(21)  # Sunday 9:00 PM Eastern
MAX_MESSAGE_LENGTH = 2000
OVERFLOW_LINE = "- … more events: see the calendar"

# Days in each message, as offsets from Monday: Mon-Tue, Wed-Fri, Sat-Sun.
DAY_GROUPS = ((0, 1), (2, 3, 4), (5, 6))
DAY_GAP = ["", ""]  # two empty lines between days, as in the manual schedule

WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
MONTHS = (
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
)  # fmt: skip


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime  # timezone-aware
    hosts: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeekMessages:
    """The text of the 3 messages, and the marker that identifies each one in Discord."""

    markers: tuple[str, ...]
    contents: tuple[str, ...]


# --- Schedule weeks -------------------------------------------------------


def schedule_day(moment: datetime) -> date:
    """Return the schedule day of ``moment``. Late-night times belong to the day before."""
    local = moment.astimezone(EASTERN)
    if local.time() < LATE_NIGHT_CUTOFF:
        return local.date() - timedelta(days=1)
    return local.date()


def week_start(moment: datetime) -> datetime:
    """Return the start (Monday 5:00 AM Eastern) of the schedule week that holds ``moment``."""
    day = schedule_day(moment)
    return _at_cutoff(day - timedelta(days=day.weekday()))


def next_week_start(start: datetime) -> datetime:
    return _at_cutoff(start.date() + timedelta(days=7))


def post_time(start: datetime) -> datetime:
    """Return the time (Sunday 9:00 PM Eastern) when the week that begins at ``start`` is posted."""
    return datetime.combine(start.date() - timedelta(days=1), POST_TIME, tzinfo=EASTERN)


def active_weeks(now: datetime) -> list[datetime]:
    """Return the week starts to sync: the current week, plus the next week after its post time."""
    current = week_start(now)
    upcoming = next_week_start(current)
    if now >= post_time(upcoming):
        return [current, upcoming]
    return [current]


def _at_cutoff(day: date) -> datetime:
    return datetime.combine(day, LATE_NIGHT_CUTOFF, tzinfo=EASTERN)


# --- Text -----------------------------------------------------------------


def ordinal(n: int) -> str:
    suffix = "TH" if 11 <= n % 100 <= 13 else {1: "ST", 2: "ND", 3: "RD"}.get(n % 10, "TH")
    return f"{n}{suffix}"


def date_text(day: date) -> str:
    """For example ``SEPTEMBER 21ST``."""
    return f"{MONTHS[day.month - 1]} {ordinal(day.day)}"


def day_heading(day: date) -> str:
    return f"**{WEEKDAYS[day.weekday()]}, {date_text(day)}**"


def week_title(start: datetime) -> str:
    monday = start.date()
    sunday = monday + timedelta(days=6)
    return f"**EVENT SCHEDULE FOR THE WEEK OF {date_text(monday)} - {date_text(sunday)}**"


def time_text(moment: datetime) -> str:
    """For example ``8:00 PM`` or ``12:30 AM``."""
    local = moment.astimezone(EASTERN)
    hour = local.hour % 12 or 12
    return f"{hour}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"


def time_zone_line(emoji: str) -> str:
    return f"{emoji} **ALL TIMES IN EST** {emoji}" if emoji else "**ALL TIMES IN EST**"


def header_lines(start: datetime, emoji: str) -> list[str]:
    return [
        week_title(start),
        "[ LATE NIGHT EVENTS APPEAR ON PRIOR DATE ]",
        "",
        "*Story events will be annotated with the following abbreviations for clarity*",
        "[O] open to everyone",
        "[I] characters initiated to any faction",
        "[A+] Apprentice and up",
        "[F] faction members only",
        "",
        time_zone_line(emoji),
    ]


def footer_lines(emoji: str, contact: str, hosts: dict[str, int]) -> list[str]:
    lines = [time_zone_line(emoji)]
    if contact:
        lines += [
            "",
            f"**Please message {host_text(contact, hosts)} if there are any questions "
            "or changes. Thank you!**",
        ]
    return lines


def event_line(event: Event, hosts: dict[str, int], with_hosts: bool = True) -> str:
    """One event line. With ``with_hosts=False`` (overflow), no mentions and no Host: part."""
    title = mention_title_names(event.title, hosts) if with_hosts else event.title
    line = f"- {time_text(event.start)} - {title}"
    if with_hosts and event.hosts:
        line += " - " + " ".join(host_text(name, hosts) for name in event.hosts)
    return line


# --- Week messages --------------------------------------------------------


def build_week_messages(
    start: datetime,
    events: Iterable[Event],
    hosts: dict[str, int],
    emoji: str = "",
    ping_everyone: bool = False,
    contact: str = "",
) -> WeekMessages:
    end = next_week_start(start)
    days = [start.date() + timedelta(days=i) for i in range(7)]
    by_day: dict[date, list[Event]] = {day: [] for day in days}
    for event in sorted(events, key=lambda e: e.start):
        if start <= event.start < end:
            by_day[schedule_day(event.start)].append(event)

    _warn_unknown_hosts(by_day, hosts)

    markers, contents = [], []
    last = len(DAY_GROUPS) - 1
    ping = ["@everyone", ""] if ping_everyone else []  # at the top of every message
    for index, group in enumerate(DAY_GROUPS):
        group_days = [days[offset] for offset in group]
        markers.append(week_title(start) if index == 0 else day_heading(group_days[0]))
        prefix = [*ping, *header_lines(start, emoji), ""] if index == 0 else ping
        suffix = [*DAY_GAP, *footer_lines(emoji, contact, hosts)] if index == last else []
        contents.append(_render(prefix, group_days, by_day, hosts, suffix))
    return WeekMessages(tuple(markers), tuple(contents))


def _render(
    prefix: list[str],
    days: list[date],
    by_day: dict[date, list[Event]],
    hosts: dict[str, int],
    suffix: list[str],
) -> str:
    for with_hosts in (True, False):
        body, event_indexes = _day_lines(days, by_day, hosts, with_hosts)
        text = "\n".join([*prefix, *body, *suffix])
        if len(text) <= MAX_MESSAGE_LENGTH:
            if not with_hosts:
                log.warning("Message for %s is too long: host names removed.", days[0])
            return text

    log.warning("Message for %s is too long: some events removed.", days[0])

    def cut_text() -> str:
        return "\n".join([*prefix, *body, OVERFLOW_LINE, *suffix])

    while event_indexes and len(cut_text()) > MAX_MESSAGE_LENGTH:
        # Remove the last event line first, so the earlier indexes stay correct.
        del body[event_indexes.pop()]
    return cut_text()


def _day_lines(
    days: list[date], by_day: dict[date, list[Event]], hosts: dict[str, int], with_hosts: bool
) -> tuple[list[str], list[int]]:
    lines: list[str] = []
    event_indexes = []
    for day in days:
        if lines:
            lines.extend(DAY_GAP)
        lines.append(day_heading(day))
        if not by_day[day]:
            lines.append("- No events")
        for event in by_day[day]:
            event_indexes.append(len(lines))
            lines.append(event_line(event, hosts, with_hosts))
    return lines, event_indexes


def _warn_unknown_hosts(by_day: dict[date, list[Event]], hosts: dict[str, int]) -> None:
    unknown = {
        name
        for events in by_day.values()
        for event in events
        for name in [*event.hosts, *title_names(event.title)]
        if name.casefold() not in hosts
    }
    for name in sorted(unknown):
        log.warning("Host %r is not a server member or in hosts.csv: plain text.", name)
