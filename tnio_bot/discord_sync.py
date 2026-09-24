"""Post and edit the week messages in the Discord channel.

``sync_week`` holds the rules (edit, post, or repost). ``DiscordChannel`` is the
only code that talks to Discord. The bot uses the REST API only: it logs in,
does its work, and closes. It needs no gateway connection and no privileged intents.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import discord

from tnio_bot.schedule import WeekMessages, post_time

# Search for the week's messages from this long before its post time.
SEARCH_MARGIN = timedelta(hours=1)


@dataclass(frozen=True)
class PostedMessage:
    id: int
    content: str


class Channel(Protocol):
    async def bot_messages_after(self, after: datetime) -> list[PostedMessage]:
        """Return this bot's messages posted after ``after``, oldest first."""
        ...

    async def send(self, content: str, *, ping_everyone: bool) -> None: ...

    async def edit(self, message_id: int, content: str) -> None: ...

    async def delete(self, message_id: int) -> None: ...


async def sync_week(
    channel: Channel, start: datetime, week: WeekMessages, ping_everyone: bool
) -> str:
    """Make the channel show ``week``. Return a short description of what changed."""
    posted = await channel.bot_messages_after(post_time(start) - SEARCH_MARGIN)
    found = [_find(posted, marker) for marker in week.markers]

    if all(found):
        edited = 0
        for message, content in zip(found, week.contents, strict=True):
            if message.content != content:
                await channel.edit(message.id, content)
                edited += 1
        return f"edited {edited} message(s)" if edited else "no changes"

    reposted = any(found)
    for message in found:
        if message:
            await channel.delete(message.id)
    for content in week.contents:
        # Each message pings @everyone on a new week, never on a repost.
        await channel.send(content, ping_everyone=ping_everyone and not reposted)
    return "reposted (a message was deleted)" if reposted else "posted"


def _find(posted: list[PostedMessage], marker: str) -> PostedMessage | None:
    return next((message for message in posted if marker in message.content), None)


class DiscordChannel:
    def __init__(self, client: discord.Client, channel: discord.abc.Messageable) -> None:
        self._client = client
        self._channel = channel

    async def bot_messages_after(self, after: datetime) -> list[PostedMessage]:
        bot_id = self._client.user.id
        return [
            PostedMessage(message.id, message.content)
            async for message in self._channel.history(after=after, limit=None, oldest_first=True)
            if message.author.id == bot_id
        ]

    async def send(self, content: str, *, ping_everyone: bool) -> None:
        mentions = discord.AllowedMentions(everyone=ping_everyone, users=False, roles=False)
        await self._channel.send(content, allowed_mentions=mentions)

    async def edit(self, message_id: int, content: str) -> None:
        message = self._channel.get_partial_message(message_id)
        await message.edit(content=content, allowed_mentions=discord.AllowedMentions.none())

    async def delete(self, message_id: int) -> None:
        await self._channel.get_partial_message(message_id).delete()


@asynccontextmanager
async def open_channel(token: str, channel_id: int) -> AsyncIterator[DiscordChannel]:
    discord.VoiceClient.warn_nacl = False  # no voice: hide the PyNaCl warning
    client = discord.Client(intents=discord.Intents.none())
    await client.login(token)
    try:
        channel = await client.fetch_channel(channel_id)
        yield DiscordChannel(client, channel)
    finally:
        await client.close()
