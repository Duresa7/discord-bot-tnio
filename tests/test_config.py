from tnio_bot.config import Settings


def test_defaults_when_env_is_empty() -> None:
    settings = Settings.from_env({})
    assert settings.discord_token is None
    assert settings.discord_channel_id is None
    assert settings.google_calendar_id == "primary"
    assert settings.ping_everyone is False
    assert settings.schedule_emoji == ""


def test_reads_values() -> None:
    settings = Settings.from_env(
        {"DISCORD_CHANNEL_ID": "123", "PING_EVERYONE": "True", "SCHEDULE_EMOJI": " <:tnio:9> "}
    )
    assert settings.discord_channel_id == 123
    assert settings.ping_everyone is True
    assert settings.schedule_emoji == "<:tnio:9>"
