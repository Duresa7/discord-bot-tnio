from pathlib import Path

from discord_bot import __version__
from discord_bot.bot import main
from discord_bot.config import Settings


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_main_returns_zero() -> None:
    assert main() == 0


def test_settings_from_env() -> None:
    settings = Settings.from_env(
        {
            "DISCORD_TOKEN": "token",
            "DISCORD_CHANNEL_ID": "123",
            "GOOGLE_CALENDAR_ID": "calendar@example.com",
        }
    )
    assert settings.discord_channel_id == 123
    assert settings.google_credentials_file == Path("credentials.json")
