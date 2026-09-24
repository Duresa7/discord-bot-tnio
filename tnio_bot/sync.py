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
from tnio_bot.discord_sync import open_channel, sync_week
from tnio_bot.hosts import load_hosts
from tnio_bot.schedule import WeekMessages, active_weeks, build_week_messages, next_week_start
from tnio_bot.status import SyncBusy, sync_lock, write_status

log = logging.getLogger(__name__)

Week = tuple[datetime, WeekMessages]


class MissingSetting(RuntimeError):
    """A setting that the sync needs is empty."""


def build_weeks(settings: config.Settings, creds, now: datetime | None = None) -> list[Week]:
    """Return the message texts of each active week."""
    hosts = load_hosts(config.HOSTS_FILE)
    server = settings.active
    weeks = []
    for start in active_weeks(now or datetime.now(config.EASTERN)):
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


async def sync_discord(settings: config.Settings, weeks: list[Week]) -> list[str]:
    """Make the active server's channel show ``weeks``. Return one result line for each week."""
    server = settings.active
    if not settings.discord_token or not server.channel_id:
        raise MissingSetting(
            f"Set the bot token and the {settings.server} server's channel ID in the settings."
        )
    results = []
    async with open_channel(settings.discord_token, server.channel_id) as channel:
        for start, messages in weeks:
            result = await sync_week(channel, start, messages, server.ping_everyone)
            results.append(f"Week of {start:%b %d}: {result}")
            log.log(logging.DEBUG if result == "no changes" else logging.INFO, results[-1])
    return results


def run_once() -> dict:
    """Sync one time, without a browser. Write ``status.json`` and return the status.

    If another sync is running, skip and leave ``status.json`` unchanged.
    """
    settings = config.load_settings()
    try:
        with sync_lock(config.LOCK_FILE):
            weeks = build_weeks(settings, get_credentials(interactive=False))
            results = asyncio.run(sync_discord(settings, weeks))
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
