import asyncio
from datetime import datetime

from tnio_bot.config import EASTERN
from tnio_bot.discord_sync import PostedMessage, sync_week
from tnio_bot.schedule import WeekMessages

WEEK = datetime(2026, 9, 21, 5, tzinfo=EASTERN)
MESSAGES = WeekMessages(
    markers=("TITLE", "WED", "SAT"),
    contents=("TITLE mon tue", "WED thu fri", "SAT sun"),
)


class FakeChannel:
    def __init__(self, contents: list[str]) -> None:
        self.messages = [PostedMessage(i, content) for i, content in enumerate(contents)]
        self.calls: list[tuple] = []

    async def bot_messages_after(self, after):
        return list(self.messages)

    async def send(self, content, *, ping_everyone):
        self.calls.append(("send", content, ping_everyone))

    async def edit(self, message_id, content):
        self.calls.append(("edit", message_id, content))

    async def delete(self, message_id):
        self.calls.append(("delete", message_id))


def sync(channel: FakeChannel, ping_everyone: bool = True) -> str:
    return asyncio.run(sync_week(channel, WEEK, MESSAGES, ping_everyone))


def test_new_week_posts_three_and_pings_once() -> None:
    channel = FakeChannel(["old week message"])
    assert sync(channel) == "posted"
    assert channel.calls == [
        ("send", "TITLE mon tue", True),
        ("send", "WED thu fri", False),
        ("send", "SAT sun", False),
    ]


def test_ping_setting_off() -> None:
    channel = FakeChannel([])
    sync(channel, ping_everyone=False)
    assert [call[2] for call in channel.calls] == [False, False, False]


def test_unchanged_week_makes_no_calls() -> None:
    channel = FakeChannel(list(MESSAGES.contents))
    assert sync(channel) == "no changes"
    assert channel.calls == []


def test_changed_message_is_edited() -> None:
    channel = FakeChannel(["other", "TITLE mon tue", "WED thu (cancelled)", "SAT sun"])
    assert sync(channel) == "edited 1 message(s)"
    assert channel.calls == [("edit", 2, "WED thu fri")]


def test_deleted_message_reposts_all_without_ping() -> None:
    channel = FakeChannel(["TITLE mon tue", "SAT sun"])  # message 2 was deleted
    assert sync(channel) == "reposted (a message was deleted)"
    assert channel.calls == [
        ("delete", 0),
        ("delete", 1),
        ("send", "TITLE mon tue", False),
        ("send", "WED thu fri", False),
        ("send", "SAT sun", False),
    ]
