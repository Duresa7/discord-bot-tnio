from datetime import datetime

import pytest

from tnio_bot.config import EASTERN
from tnio_bot.schedule import (
    MAX_MESSAGE_LENGTH,
    OVERFLOW_LINE,
    Event,
    active_weeks,
    build_week_messages,
    next_week_start,
    ordinal,
    post_time,
    schedule_day,
    time_text,
    week_start,
)


def et(*args: int) -> datetime:
    return datetime(*args, tzinfo=EASTERN)


WEEK = et(2026, 9, 21, 5)  # Monday
NEXT_WEEK = et(2026, 9, 28, 5)


# --- Schedule weeks ---


def test_late_night_belongs_to_day_before() -> None:
    assert schedule_day(et(2026, 9, 23, 1)).day == 22
    assert schedule_day(et(2026, 9, 23, 5)).day == 23


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (et(2026, 9, 23, 12), WEEK),
        (et(2026, 9, 21, 5), WEEK),
        (et(2026, 9, 21, 4, 59), et(2026, 9, 14, 5)),  # Monday late night = previous Sunday
        (et(2026, 9, 28, 4, 59), WEEK),
    ],
)
def test_week_start(moment: datetime, expected: datetime) -> None:
    assert week_start(moment) == expected


def test_week_start_accepts_utc() -> None:
    assert week_start(datetime.fromisoformat("2026-09-23T16:00:00+00:00")) == WEEK


def test_next_week_over_dst_change() -> None:
    # DST ends on Sunday 2026-11-01. The next week still starts at 5:00 AM local time.
    start = next_week_start(et(2026, 10, 26, 5))
    assert start == et(2026, 11, 2, 5)
    assert start.utcoffset().total_seconds() == -5 * 3600
    assert post_time(start) == et(2026, 11, 1, 21)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (et(2026, 9, 27, 20, 59), [WEEK]),
        (et(2026, 9, 27, 21, 0), [WEEK, NEXT_WEEK]),
        (et(2026, 9, 28, 4, 59), [WEEK, NEXT_WEEK]),
        (et(2026, 9, 28, 5, 0), [NEXT_WEEK]),
    ],
)
def test_active_weeks(now: datetime, expected: list[datetime]) -> None:
    assert active_weeks(now) == expected


# --- Text ---


@pytest.mark.parametrize(
    ("n", "text"),
    [(1, "1ST"), (2, "2ND"), (3, "3RD"), (4, "4TH"), (11, "11TH"), (12, "12TH"), (13, "13TH"),
     (21, "21ST"), (22, "22ND"), (23, "23RD"), (31, "31ST")],
)  # fmt: skip
def test_ordinal(n: int, text: str) -> None:
    assert ordinal(n) == text


def test_time_text() -> None:
    assert time_text(et(2026, 9, 21, 0, 0)) == "12:00 AM"
    assert time_text(et(2026, 9, 21, 12, 30)) == "12:30 PM"
    assert time_text(et(2026, 9, 21, 20, 5)) == "8:05 PM"


# --- Week messages ---


def test_full_week_layout() -> None:
    events = [
        Event("Sith Academy", et(2026, 9, 21, 21), ("Vistenia",)),
        Event("Praetorian Training", et(2026, 9, 21, 20), ("Blackeye",)),
        Event("Force Pantheon (F)", et(2026, 9, 22, 0), ("Kaelis",)),  # Monday late night
        Event("Tournament", et(2026, 9, 26, 20)),
    ]
    week = build_week_messages(
        WEEK, events, {"blackeye": 111}, emoji="<:tnio:9>", ping_everyone=True
    )

    assert week.contents[0] == "\n".join(
        [
            "@everyone",
            "",
            "**EVENT SCHEDULE FOR THE WEEK OF SEPTEMBER 21ST - SEPTEMBER 27TH**",
            "[ LATE NIGHT EVENTS APPEAR ON PRIOR DATE ]",
            "",
            "*Story events will be annotated with the following abbreviations for clarity*",
            "[O] open to everyone",
            "[I] characters initiated to any faction",
            "[A+] Apprentice and up",
            "[F] faction members only",
            "",
            "<:tnio:9> **ALL TIMES IN EST** <:tnio:9>",
            "",
            "**MONDAY, SEPTEMBER 21ST**",
            "- 8:00 PM - Praetorian Training - <@111>",
            "- 9:00 PM - Sith Academy - Vistenia",
            "- 12:00 AM - Force Pantheon (F) - Kaelis",
            "",
            "",
            "**TUESDAY, SEPTEMBER 22ND**",
            "- No events",
        ]
    )
    assert week.contents[1].startswith(
        "@everyone\n\n**WEDNESDAY, SEPTEMBER 23RD**\n- No events\n\n\n"
    )
    assert week.contents[2] == "\n".join(
        [
            "@everyone",
            "",
            "**SATURDAY, SEPTEMBER 26TH**",
            "- 8:00 PM - Tournament",
            "",
            "",
            "**SUNDAY, SEPTEMBER 27TH**",
            "- No events",
            "",
            "",
            "<:tnio:9> **ALL TIMES IN EST** <:tnio:9>",
        ]
    )
    assert week.markers == (
        "**EVENT SCHEDULE FOR THE WEEK OF SEPTEMBER 21ST - SEPTEMBER 27TH**",
        "**WEDNESDAY, SEPTEMBER 23RD**",
        "**SATURDAY, SEPTEMBER 26TH**",
    )


def test_no_ping_no_emoji() -> None:
    week = build_week_messages(WEEK, [], {})
    assert week.contents[0].startswith("**EVENT SCHEDULE")
    assert week.contents[1].startswith("**WEDNESDAY")
    assert week.contents[2].startswith("**SATURDAY")
    assert "@everyone" not in "".join(week.contents)
    assert "\n**ALL TIMES IN EST**\n" in week.contents[0]


def test_events_outside_the_week_are_ignored() -> None:
    events = [
        Event("Before", et(2026, 9, 21, 4, 59)),  # previous week's Sunday late night
        Event("After", et(2026, 9, 28, 5)),  # next week
        Event("Last", et(2026, 9, 28, 4, 59)),  # this week's Sunday late night
    ]
    week = build_week_messages(WEEK, events, {})
    text = "\n".join(week.contents)
    assert "Before" not in text
    assert "After" not in text
    assert "**SUNDAY, SEPTEMBER 27TH**\n- 4:59 AM - Last\n" in week.contents[2]


def test_footer_with_contact() -> None:
    week = build_week_messages(WEEK, [], {"rakkos": 42}, contact="Rakkos")
    assert week.contents[2].endswith(
        "- No events\n\n\n**ALL TIMES IN EST**\n\n"
        "**Please message <@42> if there are any questions or changes. Thank you!**"
    )


def test_overflow_note_comes_before_the_footer() -> None:
    saturday = [
        Event(f"Event number {i:02d} " + "x" * 40, et(2026, 9, 26, 6 + i % 17, i % 60))
        for i in range(60)
    ]
    content = build_week_messages(WEEK, saturday, {}, contact="Rakkos").contents[2]
    assert len(content) <= MAX_MESSAGE_LENGTH
    assert f"{OVERFLOW_LINE}\n\n\n**ALL TIMES IN EST**" in content
    assert content.endswith("Thank you!**")


def many_events(count: int) -> list[Event]:
    """Events on Wednesday (message 2), each line about 60 characters long."""
    return [
        Event(f"Event number {i:02d} " + "x" * 40, et(2026, 9, 23, 6 + i % 17, i % 60), ("Host",))
        for i in range(count)
    ]


def test_overflow_removes_hosts_first() -> None:
    hosts = {"host": 123456789012345678}
    content = build_week_messages(WEEK, many_events(26), hosts).contents[1]
    assert len(content) <= MAX_MESSAGE_LENGTH
    assert "<@" not in content
    assert OVERFLOW_LINE not in content
    assert content.count("Event number") == 26


def test_overflow_cuts_last_events() -> None:
    content = build_week_messages(WEEK, many_events(60), {}).contents[1]
    assert len(content) <= MAX_MESSAGE_LENGTH
    assert content.endswith(OVERFLOW_LINE)
    assert 0 < content.count("Event number") < 60
