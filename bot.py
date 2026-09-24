"""Sync the weekly schedule messages with Google Calendar.

Windows Task Scheduler runs this every 5 minutes. Each run syncs, then stops.

    python bot.py            sync the Discord messages
    python bot.py --preview  print the messages only (no Discord)
    python bot.py --sign-in  sign in to Google (browser), then print the next 10 events
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from tnio_bot.calendar_sync import fetch_week_events, get_credentials, print_upcoming_events
from tnio_bot.config import EASTERN, HOSTS_FILE, LOG_FILE, load_settings
from tnio_bot.discord_sync import open_channel, sync_week
from tnio_bot.hosts import load_hosts
from tnio_bot.schedule import WeekMessages, active_weeks, build_week_messages, next_week_start

log = logging.getLogger("bot")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true", help="print the messages only")
    mode.add_argument("--sign-in", action="store_true", help="sign in to Google, print 10 events")
    args = parser.parse_args(argv)

    if args.sign_in:
        print_upcoming_events(load_settings().google_calendar_id)
        return 0

    setup_logging()
    try:
        asyncio.run(run(preview=args.preview))
    except Exception:
        log.exception("Run failed")
        return 1
    return 0


async def run(preview: bool) -> None:
    settings = load_settings()
    hosts = load_hosts(HOSTS_FILE)
    # A preview runs by hand, so it can open the browser sign-in. A scheduled run cannot.
    creds = get_credentials(interactive=preview)

    weeks: list[tuple[datetime, WeekMessages]] = []
    for start in active_weeks(datetime.now(EASTERN)):
        events = fetch_week_events(
            creds, settings.google_calendar_id, start, next_week_start(start)
        )
        messages = build_week_messages(
            start, events, hosts, settings.schedule_emoji, settings.ping_everyone
        )
        weeks.append((start, messages))

    if preview:
        for start, messages in weeks:
            for number, content in enumerate(messages.contents, start=1):
                print(f"===== Week of {start:%Y-%m-%d}, message {number} ({len(content)} chars)")
                print(content)
        return

    if not settings.discord_token or not settings.discord_channel_id:
        raise RuntimeError("Set DISCORD_TOKEN and DISCORD_CHANNEL_ID in .env")

    async with open_channel(settings.discord_token, settings.discord_channel_id) as channel:
        for start, messages in weeks:
            result = await sync_week(channel, start, messages, settings.ping_everyone)
            level = logging.DEBUG if result == "no changes" else logging.INFO
            log.log(level, "Week of %s: %s", f"{start:%Y-%m-%d}", result)


def setup_logging() -> None:
    handlers: list[logging.Handler] = [
        RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    ]
    if sys.stderr is not None:  # pythonw.exe (Task Scheduler) has no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    logging.getLogger("discord").setLevel(logging.WARNING)


if __name__ == "__main__":
    raise SystemExit(main())
