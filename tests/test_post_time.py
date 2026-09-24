import asyncio
from datetime import datetime, time, timedelta

import pytest

from tnio_bot.config import EASTERN, Settings
from tnio_bot.discord_sync import sync_week
from tnio_bot.schedule import WeekMessages, active_weeks, next_post_time, post_time


def et(*args: int) -> datetime:
    return datetime(*args, tzinfo=EASTERN)


WEEK = et(2026, 9, 28, 5)  # Monday


@pytest.mark.parametrize(
    ("day", "at", "expected"),
    [
        (6, time(21), et(2026, 9, 27, 21)),  # default: Sunday 9 PM
        (4, time(18, 30), et(2026, 9, 25, 18, 30)),  # Friday 6:30 PM
        (0, time(12), et(2026, 9, 21, 12)),  # Monday noon, one week early
        (0, time(3), et(2026, 9, 28, 3)),  # Monday 3 AM = the late night just before
    ],
)
def test_post_time(day: int, at: time, expected: datetime) -> None:
    moment = post_time(WEEK, day, at)
    assert moment == expected
    assert WEEK - timedelta(days=7) <= moment < WEEK


def test_active_weeks_with_friday_post() -> None:
    assert active_weeks(et(2026, 9, 25, 18, 29), 4, time(18, 30)) == [et(2026, 9, 21, 5)]
    assert active_weeks(et(2026, 9, 25, 18, 30), 4, time(18, 30)) == [et(2026, 9, 21, 5), WEEK]


def test_next_post_time() -> None:
    assert next_post_time(et(2026, 9, 24, 12)) == et(2026, 9, 27, 21)
    assert next_post_time(et(2026, 9, 27, 21)) == et(2026, 10, 4, 21)  # just posted


def test_settings_post_day_and_time() -> None:
    settings = Settings.from_env({"POST_DAY": "Friday", "POST_TIME": "18:30"})
    assert (settings.post_day, settings.post_time) == (4, time(18, 30))
    default = Settings.from_env({"POST_DAY": "someday", "POST_TIME": "late"})
    assert (default.post_day, default.post_time) == (6, time(21))


class RecordingChannel:
    after = None

    async def bot_messages_after(self, after):
        self.after = after
        return []

    async def send(self, content, *, ping_everyone):
        pass


def test_search_does_not_depend_on_the_post_time() -> None:
    channel = RecordingChannel()
    week = WeekMessages(markers=("A", "B", "C"), contents=("A", "B", "C"))
    asyncio.run(sync_week(channel, WEEK, week, ping_everyone=False))
    assert channel.after <= WEEK - timedelta(days=7)
