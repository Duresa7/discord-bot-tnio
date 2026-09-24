from tnio_bot.config import Settings, update_env_file


def test_defaults_when_env_is_empty() -> None:
    settings = Settings.from_env({})
    assert settings.discord_token is None
    assert settings.server == "test"
    assert settings.google_calendar_id == "primary"
    assert settings.active.channel_id is None
    assert settings.active.ping_everyone is False
    assert settings.active.emoji == ""


def test_active_server_settings() -> None:
    env = {
        "DISCORD_SERVER": "Real",
        "TEST_CHANNEL_ID": "111",
        "REAL_CHANNEL_ID": "222",
        "REAL_PING_EVERYONE": "True",
        "REAL_SCHEDULE_EMOJI": " <:tnio:9> ",
    }
    settings = Settings.from_env(env)
    assert settings.server == "real"
    assert settings.test.channel_id == 111
    assert settings.active.channel_id == 222
    assert settings.active.ping_everyone is True
    assert settings.active.emoji == "<:tnio:9>"


def test_unknown_server_and_bad_channel_fall_back() -> None:
    settings = Settings.from_env({"DISCORD_SERVER": "prod", "TEST_CHANNEL_ID": "abc"})
    assert settings.server == "test"
    assert settings.test.channel_id is None


def test_update_env_file_keeps_comments_and_adds_keys(tmp_path) -> None:
    path = tmp_path / ".env"
    path.write_text("# comment\nDISCORD_TOKEN=old\nTEST_CHANNEL_ID=\n", encoding="utf-8")
    update_env_file(path, {"DISCORD_TOKEN": "new\n", "REAL_CHANNEL_ID": "5"})
    assert path.read_text(encoding="utf-8") == (
        "# comment\nDISCORD_TOKEN=new\nTEST_CHANNEL_ID=\nREAL_CHANNEL_ID=5\n"
    )


def test_update_env_file_creates_file(tmp_path) -> None:
    path = tmp_path / ".env"
    update_env_file(path, {"DISCORD_SERVER": "real"})
    assert path.read_text(encoding="utf-8") == "DISCORD_SERVER=real\n"
