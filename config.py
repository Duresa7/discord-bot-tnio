"""Configuration loaded from environment variables (placeholder structure).

Values come from a local ``.env`` file (see ``.env.example``). Git ignores
``.env``. Do not put secrets in this file.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Local files. Never commit them.
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")

# Read-only access. The app never changes the calendar.
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@dataclass(frozen=True)
class Settings:
    discord_token: str | None
    discord_channel_id: int | None
    discord_message_id: int | None
    google_calendar_id: str

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Settings":
        return cls(
            discord_token=env.get("DISCORD_TOKEN") or None,
            discord_channel_id=_optional_int(env.get("DISCORD_CHANNEL_ID")),
            discord_message_id=_optional_int(env.get("DISCORD_MESSAGE_ID")),
            google_calendar_id=env.get("GOOGLE_CALENDAR_ID") or "primary",
        )


def load_settings() -> Settings:
    """Read ``.env`` into the environment, then build the settings."""
    from dotenv import load_dotenv

    load_dotenv()
    return Settings.from_env(dict(os.environ))


def _optional_int(value: str | None) -> int | None:
    return int(value) if value else None
