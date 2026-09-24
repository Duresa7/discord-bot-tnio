"""Configuration loaded from environment variables (placeholder structure).

The variable names are listed in ``.env.example``. Real values go in a local
``.env`` file, which git ignores. Do not put secrets in this file.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    discord_token: str
    discord_channel_id: int
    google_calendar_id: str
    google_credentials_file: Path

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = dict(os.environ) if env is None else env
        return cls(
            discord_token=env["DISCORD_TOKEN"],
            discord_channel_id=int(env["DISCORD_CHANNEL_ID"]),
            google_calendar_id=env["GOOGLE_CALENDAR_ID"],
            google_credentials_file=Path(env.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")),
        )
