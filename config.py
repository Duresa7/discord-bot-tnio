"""Configuration loaded from environment variables.

Values come from a local ``.env`` file (see ``.env.example``). Git ignores
``.env``. Do not put secrets in this file.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

# All paths start from the project folder, because Task Scheduler does not
# start the bot in that folder.
BASE_DIR = Path(__file__).resolve().parent

# Local files. Never commit them.
ENV_FILE = BASE_DIR / ".env"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
LOG_FILE = BASE_DIR / "bot.log"

# Committed: short host name -> Discord user ID.
HOSTS_FILE = BASE_DIR / "hosts.csv"

# Read-only access. The app never changes the calendar.
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Settings:
    discord_token: str | None
    discord_channel_id: int | None
    google_calendar_id: str
    ping_everyone: bool
    schedule_emoji: str

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Settings":
        return cls(
            discord_token=env.get("DISCORD_TOKEN") or None,
            discord_channel_id=_optional_int(env.get("DISCORD_CHANNEL_ID")),
            google_calendar_id=env.get("GOOGLE_CALENDAR_ID") or "primary",
            ping_everyone=env.get("PING_EVERYONE", "").strip().lower() == "true",
            schedule_emoji=env.get("SCHEDULE_EMOJI", "").strip(),
        )


def load_settings() -> Settings:
    """Read ``.env`` into the environment, then build the settings."""
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE)
    return Settings.from_env(dict(os.environ))


def _optional_int(value: str | None) -> int | None:
    return int(value) if value else None
