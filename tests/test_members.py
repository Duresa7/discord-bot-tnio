import asyncio
from datetime import datetime
from types import SimpleNamespace

import discord

from tnio_bot.config import EASTERN
from tnio_bot.hosts import MemberInfo, member_name_map, mention_title_names, title_names
from tnio_bot.schedule import Event, event_line
from tnio_bot.sync import MEMBERS_INTENT_HELP, fetch_members

WOLF = MemberInfo(1, "wolfdiesalot", "WolfDiesAlot", "Grand Inquisitor Wolf")
RAVEN = MemberInfo(2, "ravenblack18102", None, None)


def test_member_name_map_uses_username_display_name_and_nickname() -> None:
    names = member_name_map([WOLF, RAVEN])
    assert names["wolfdiesalot"] == 1
    assert names["grand inquisitor wolf"] == 1
    assert names["ravenblack18102"] == 2


def test_shared_display_name_is_left_out_but_username_wins() -> None:
    a = MemberInfo(1, "alpha", "Shadow", None)
    b = MemberInfo(2, "beta", None, "Shadow")
    c = MemberInfo(3, "shadow", None, None)  # username "shadow"
    assert member_name_map([a, b])["alpha"] == 1
    assert "shadow" not in member_name_map([a, b])
    assert member_name_map([a, b, c])["shadow"] == 3


def test_title_names() -> None:
    assert title_names("INQ: Hide and Seeker Pt.3 Finale [F] - @WolfDiesAlot") == ["WolfDiesAlot"]
    assert title_names("Intel Training - @ravenblack18102.") == ["ravenblack18102"]
    assert title_names("**OPEN ROLEPLAY**") == []
    assert title_names("Mail me at a@b.com - @everyone") == []


def test_mention_title_names() -> None:
    names = member_name_map([WOLF, RAVEN])
    assert mention_title_names("Hide [F] - @WolfDiesAlot", names) == "Hide [F] - <@1>"
    assert mention_title_names("Training - @ravenblack18102.", names) == "Training - <@2>."
    assert mention_title_names("Training - @Nobody", names) == "Training - @Nobody"
    assert mention_title_names("Ping @everyone", names) == "Ping @everyone"


def test_event_line_mentions_title_names_and_overflow_keeps_text() -> None:
    event = Event("Intel Training - @ravenblack18102", datetime(2026, 9, 24, 23, tzinfo=EASTERN))
    names = member_name_map([RAVEN])
    assert event_line(event, names) == "- 11:00 PM - Intel Training - <@2>"
    assert (
        event_line(event, names, with_hosts=False)
        == "- 11:00 PM - Intel Training - @ravenblack18102"
    )


class MembersChannel:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def members(self):
        if self.error:
            raise self.error
        return [WOLF]


def test_fetch_members_ok() -> None:
    assert asyncio.run(fetch_members(MembersChannel())) == ([WOLF], None)


def test_fetch_members_without_the_intent_gives_help() -> None:
    forbidden = discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "Missing Access")
    assert asyncio.run(fetch_members(MembersChannel(forbidden))) == ([], MEMBERS_INTENT_HELP)
