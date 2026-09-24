"""One sync run: read the calendar, build the week messages, update Discord.

Used by ``bot.py`` (the scheduled task) and by the control panel.
"""

import asyncio
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

import discord
import httplib2
from google.auth.exceptions import TransportError
from googleapiclient.errors import HttpError

from tnio_bot import config
from tnio_bot.calendar_sync import (
    MissingCredentials,
    SignInRequired,
    fetch_week_events,
    get_credentials,
)
from tnio_bot.discord_sync import DiscordChannel, open_channel, sync_week
from tnio_bot.hosts import MemberInfo, load_hosts, member_name_map
from tnio_bot.schedule import WeekMessages, active_weeks, build_week_messages, next_week_start
from tnio_bot.status import SyncBusy, sync_lock, write_status

log = logging.getLogger(__name__)

Week = tuple[datetime, WeekMessages]

MEMBERS_INTENT_HELP = (
    "@names show as plain text. Turn on 'Server Members Intent' on the Bot page of "
    "the Discord Developer Portal."
)


class MissingSetting(RuntimeError):
    """A setting that the sync needs is empty."""


def build_weeks(
    settings: config.Settings,
    creds,
    now: datetime | None = None,
    members: list[MemberInfo] | None = None,
) -> list[Week]:
    """Return the message texts of each active week.

    ``members`` (the server's member list) turns ``@name`` into mentions;
    ``data/hosts.csv`` entries win over member names.
    """
    hosts = {**member_name_map(members or []), **load_hosts(config.HOSTS_FILE)}
    server = settings.active
    weeks = []
    now = now or datetime.now(config.EASTERN)
    for start in active_weeks(now, settings.post_day, settings.post_time):
        events = fetch_week_events(
            creds, settings.google_calendar_id, start, next_week_start(start)
        )
        weeks.append(
            (
                start,
                build_week_messages(
                    start,
                    events,
                    hosts,
                    server.emoji,
                    server.ping_everyone,
                    settings.contact_host,
                ),
            )
        )
    return weeks


async def sync_discord(settings: config.Settings, creds) -> list[str]:
    """Make the active server's channel show the active weeks. Return the result lines."""
    server = settings.active
    if not settings.discord_token or not server.channel_id:
        raise MissingSetting(
            f"Set the bot token and the {settings.server} server's channel ID in the settings."
        )
    results = []
    async with open_channel(settings.discord_token, server.channel_id) as channel:
        members, note = await fetch_members(channel)
        for start, messages in build_weeks(settings, creds, members=members):
            result = await sync_week(channel, start, messages, server.ping_everyone)
            results.append(f"Week of {start:%b %d}: {result}")
            log.log(logging.DEBUG if result == "no changes" else logging.INFO, results[-1])
    if note:
        results.append(f"Note: {note}")
    return results


async def preview_weeks(
    settings: config.Settings, creds
) -> tuple[list[Week], list[MemberInfo], str | None]:
    """Build the active weeks for a preview. Read the member list if Discord is set up."""
    members, note = [], None
    if settings.discord_token and settings.active.channel_id:
        try:
            async with open_channel(settings.discord_token, settings.active.channel_id) as channel:
                members, note = await fetch_members(channel)
        except Exception as error:
            note = f"@names show as plain text: {friendly_error(error)}"
    else:
        note = "Set the bot token and the channel ID to show @names as blue mentions."
    return build_weeks(settings, creds, members=members), members, note


async def fetch_members(channel: DiscordChannel) -> tuple[list[MemberInfo], str | None]:
    """Return the server's members, or no members and a note that explains why."""
    try:
        return await channel.members(), None
    except discord.Forbidden:
        log.warning("Member list not available: Server Members Intent is off.")
        return [], MEMBERS_INTENT_HELP
    except Exception as error:
        log.warning("Member list not available: %s", error)
        return [], f"@names show as plain text: {friendly_error(error)}"


def run_once() -> dict:
    """Sync one time, without a browser. Write ``status.json`` and return the status.

    If another sync is running, skip and leave ``status.json`` unchanged.
    """
    settings = config.load_settings()
    try:
        with sync_lock(config.LOCK_FILE):
            results = asyncio.run(sync_discord(settings, get_credentials(interactive=False)))
    except SyncBusy as error:
        log.info("%s", error)
        return {"ok": False, "skipped": True, "error": str(error)}
    except Exception as error:
        log.exception("Sync failed")
        return write_status(
            config.STATUS_FILE,
            server=settings.server,
            ok=False,
            results=[],
            error=friendly_error(error),
        )
    return write_status(
        config.STATUS_FILE, server=settings.server, ok=True, results=results, error=None
    )


def friendly_error(error: BaseException) -> str:
    """Explain ``error`` in plain words for the control panel."""
    if isinstance(error, SignInRequired):
        return "Google sign-in is necessary. Click 'Sign in to Google'."
    if isinstance(error, MissingCredentials | MissingSetting):
        return str(error)
    if isinstance(error, discord.LoginFailure):
        return "Discord did not accept the bot token. Paste a new token in Settings."
    if isinstance(error, discord.Forbidden):
        return (
            "The bot has no permission in the schedule channel. It needs: View Channel, "
            "Send Messages, Read Message History, Mention Everyone."
        )
    if isinstance(error, discord.NotFound):
        return (
            "Discord channel not found. Check the channel ID, and that the bot is in that server."
        )
    if isinstance(error, HttpError) and error.resp.status == 404:
        return (
            "Google Calendar not found. Check the calendar ID, and that the signed-in "
            "account can see that calendar."
        )
    if isinstance(error, discord.HTTPException | HttpError):
        return f"Discord or Google returned an error: {error}"
    if isinstance(error, OSError | TransportError | httplib2.HttpLib2Error):
        return (
            "No internet connection, or Discord or Google did not answer. The next run tries again."
        )
    return f"Unexpected error: {error}"


def setup_logging() -> None:
    handlers: list[logging.Handler] = [
        RotatingFileHandler(config.LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    ]
    if sys.stderr is not None:  # pythonw.exe (Task Scheduler) has no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    logging.getLogger("discord").setLevel(logging.WARNING)
