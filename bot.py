"""Sync the weekly schedule messages with Google Calendar.

Windows Task Scheduler runs this every 5 minutes. Each run syncs, then stops.
The friend normally uses the control panel instead ("Start Control Panel.bat").

    python bot.py            sync the Discord messages
    python bot.py --preview  print the messages only (no Discord)
    python bot.py --sign-in  sign in to Google (browser), then print the next 10 events
"""

import argparse

from tnio_bot.calendar_sync import get_credentials, print_upcoming_events
from tnio_bot.config import load_settings
from tnio_bot.sync import build_weeks, run_once, setup_logging


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
    if args.preview:
        for start, messages in build_weeks(load_settings(), get_credentials(interactive=True)):
            for number, content in enumerate(messages.contents, start=1):
                print(f"===== Week of {start:%Y-%m-%d}, message {number} ({len(content)} chars)")
                print(content)
        return 0

    status = run_once()
    return 0 if status["ok"] or status.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
