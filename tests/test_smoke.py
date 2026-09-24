from bot import main
from config import Settings


def test_main_returns_zero() -> None:
    assert main() == 0


def test_settings_defaults_when_env_is_empty() -> None:
    settings = Settings.from_env({})
    assert settings.discord_token is None
    assert settings.discord_message_id is None
    assert settings.google_calendar_id == "primary"


def test_settings_reads_ids_as_int() -> None:
    settings = Settings.from_env({"DISCORD_CHANNEL_ID": "123", "DISCORD_MESSAGE_ID": "456"})
    assert settings.discord_channel_id == 123
    assert settings.discord_message_id == 456
