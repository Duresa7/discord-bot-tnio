"""Configuration from the local ``.env`` file, and all file paths.

See ``.env.example`` for the keys. Git ignores ``.env``. Do not put secrets in
this file.
"""

import os
from dataclasses import dataclass, replace
from datetime import time
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
FOOTER_FILE = BASE_DIR / "data" / "footer.txt"

# Read-only access. The app never changes the calendar.
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

EASTERN = ZoneInfo("America/New_York")

SERVERS = ("test", "real")

DAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DEFAULT_POST_DAY = 6  # Sunday
DEFAULT_POST_TIME = time(21)  # 9:00 PM Eastern

# End of message 3. "{emoji}" = the active server's emoji; "@name" = a mention.
DEFAULT_FOOTER = "{emoji} **ALL TIMES IN EST** {emoji}"
CONTACT_LINE = "**Please message @{name} if there are any questions or changes. Thank you!**"
MAX_FOOTER_LENGTH = 500


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
    footer: str = DEFAULT_FOOTER  # text at the end of message 3
    post_day: int = DEFAULT_POST_DAY  # weekday (Monday = 0) when the next week is posted
    post_time: time = DEFAULT_POST_TIME  # Eastern

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
            footer=default_footer(env.get("CONTACT_HOST")),
            post_day=parse_day(env.get("POST_DAY")),
            post_time=parse_time(env.get("POST_TIME")),
        )


def parse_day(value: str | None) -> int:
    """``"sunday"`` -> 6. An empty or unknown value gives the default (Sunday)."""
    name = (value or "").strip().lower()
    return DAY_NAMES.index(name) if name in DAY_NAMES else DEFAULT_POST_DAY


def parse_time(value: str | None) -> time:
    """``"21:00"`` -> 9:00 PM. An empty or wrong value gives the default (9:00 PM)."""
    try:
        return time.fromisoformat((value or "").strip())
    except ValueError:
        return DEFAULT_POST_TIME


def default_footer(contact: str | None = None) -> str:
    """The footer until it is changed in the panel.

    Older versions had a contact setting (``CONTACT_HOST``). Its line stays in the footer.
    """
    contact = (contact or "").strip()
    return f"{DEFAULT_FOOTER}\n\n{CONTACT_LINE.format(name=contact)}" if contact else DEFAULT_FOOTER


def load_settings() -> Settings:
    """Read the settings. Values in ``.env`` win over the process environment."""
    from dotenv import dotenv_values

    values = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    settings = Settings.from_env(
        {**os.environ, **{k: v for k, v in values.items() if v is not None}}
    )
    if FOOTER_FILE.exists():
        settings = replace(settings, footer=FOOTER_FILE.read_text(encoding="utf-8-sig"))
    return settings


def clean_footer(text: str) -> str:
    """Use ``\\n`` line breaks, and remove the empty lines at the start and the end."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def write_footer(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(clean_footer(text), encoding="utf-8", newline="\n")


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
