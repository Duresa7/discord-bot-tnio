"""Configuration from the local ``.env`` file, and all file paths.

See ``.env.example`` for the keys. Git ignores ``.env``. Do not put secrets in
this file.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

# All paths start from the project folder (one level above this package),
# because Task Scheduler does not start the bot in that folder.
BASE_DIR = Path(__file__).resolve().parent.parent

# Local files. Never commit them.
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE_FILE = BASE_DIR / ".env.example"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
LOG_FILE = BASE_DIR / "bot.log"
STATUS_FILE = BASE_DIR / "status.json"
LOCK_FILE = BASE_DIR / "sync.lock"
HOSTS_FILE = BASE_DIR / "data" / "hosts.csv"

# Read-only access. The app never changes the calendar.
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

EASTERN = ZoneInfo("America/New_York")

SERVERS = ("test", "real")


@dataclass(frozen=True)
class ServerSettings:
    channel_id: int | None
    emoji: str
    ping_everyone: bool


@dataclass(frozen=True)
class Settings:
    discord_token: str | None
    server: str  # "test" or "real"
    test: ServerSettings
    real: ServerSettings
    google_calendar_id: str

    @property
    def active(self) -> ServerSettings:
        """The settings of the server that the bot posts to now."""
        return self.real if self.server == "real" else self.test

    @classmethod
    def from_env(cls, env: dict[str, str]) -> "Settings":
        server = (env.get("DISCORD_SERVER") or "test").strip().lower()
        return cls(
            discord_token=(env.get("DISCORD_TOKEN") or "").strip() or None,
            server=server if server in SERVERS else "test",
            test=_server(env, "TEST"),
            real=_server(env, "REAL"),
            google_calendar_id=(env.get("GOOGLE_CALENDAR_ID") or "").strip() or "primary",
        )


def load_settings() -> Settings:
    """Read the settings. Values in ``.env`` win over the process environment."""
    from dotenv import dotenv_values

    values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    return Settings.from_env({**os.environ, **{k: v for k, v in values.items() if v is not None}})


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Set ``KEY=value`` lines in ``path``. Keep other lines and comments; add missing keys."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = {key: _clean(value) for key, value in updates.items()}
    for index, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if "=" in line and not line.lstrip().startswith("#") and key in remaining:
            lines[index] = f"{key}={remaining.pop(key)}"
    lines.extend(f"{key}={value}" for key, value in remaining.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _server(env: dict[str, str], prefix: str) -> ServerSettings:
    channel = (env.get(f"{prefix}_CHANNEL_ID") or "").strip()
    return ServerSettings(
        channel_id=int(channel) if channel.isdigit() else None,
        emoji=(env.get(f"{prefix}_SCHEDULE_EMOJI") or "").strip(),
        ping_everyone=(env.get(f"{prefix}_PING_EVERYONE") or "").strip().lower() == "true",
    )


def _clean(value: str) -> str:
    # One line only; no quotes, so python-dotenv reads the value back unchanged.
    return str(value).replace("\r", " ").replace("\n", " ").replace('"', "").strip()
