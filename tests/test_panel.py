import pytest

from tnio_bot import config, panel, task

BASE_URL = "http://localhost:8765"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(config, "ENV_EXAMPLE_FILE", tmp_path / ".env.example")
    monkeypatch.setattr(config, "HOSTS_FILE", tmp_path / "data" / "hosts.csv")
    monkeypatch.setattr(config, "STATUS_FILE", tmp_path / "status.json")
    monkeypatch.setattr(panel, "sign_in_problem", lambda: None)
    monkeypatch.setattr(task, "is_on", lambda: False)
    for key in (
        "DISCORD_TOKEN",
        "DISCORD_SERVER",
        "GOOGLE_CALENDAR_ID",
        "CONTACT_HOST",
        "POST_DAY",
        "POST_TIME",
    ):
        monkeypatch.delenv(key, raising=False)
    return panel.app.test_client()


def test_state_hides_the_token(client) -> None:
    config.ENV_FILE.write_text("DISCORD_TOKEN=secret-value\n", encoding="utf-8")
    response = client.get("/api/state", base_url=BASE_URL)
    assert response.status_code == 200
    assert response.json["token_set"] is True
    assert "secret-value" not in response.get_data(as_text=True)


def test_other_host_names_are_blocked(client) -> None:
    assert client.get("/api/state", base_url="http://evil.example:8765").status_code == 403


def test_write_needs_json(client) -> None:
    response = client.post("/api/settings", base_url=BASE_URL, data="server=real")
    assert response.status_code == 415


def test_write_from_other_website_is_blocked(client) -> None:
    response = client.post(
        "/api/settings",
        base_url=BASE_URL,
        json={"server": "real"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_save_settings(client) -> None:
    config.ENV_EXAMPLE_FILE.write_text("# example\nDISCORD_TOKEN=\n", encoding="utf-8")
    body = {
        "server": "real",
        "token": " new-token ",
        "real": {"channel_id": "222", "emoji": "<:tnio:9>", "ping_everyone": True},
    }
    assert client.post("/api/settings", base_url=BASE_URL, json=body).status_code == 200
    settings = config.load_settings()
    assert settings.server == "real"
    assert settings.discord_token == "new-token"
    assert settings.active.channel_id == 222
    assert settings.active.ping_everyone is True
    assert config.ENV_FILE.read_text(encoding="utf-8").startswith("# example\n")


def test_empty_token_keeps_the_old_one(client) -> None:
    config.ENV_FILE.write_text("DISCORD_TOKEN=old\n", encoding="utf-8")
    client.post("/api/settings", base_url=BASE_URL, json={"token": "", "calendar_id": "x"})
    assert config.load_settings().discord_token == "old"


def test_bad_channel_id_is_refused(client) -> None:
    body = {"test": {"channel_id": "abc"}}
    response = client.post("/api/settings", base_url=BASE_URL, json=body)
    assert response.status_code == 400
    assert "digits" in response.json["error"]


def test_contact_must_be_in_the_host_list(client) -> None:
    body = {"contact_host": "Rakkos"}
    response = client.post("/api/settings", base_url=BASE_URL, json=body)
    assert response.status_code == 400
    assert "not in the host list" in response.json["error"]

    hosts = [{"name": "Rakkos", "discord_id": "123456789012345678"}]
    client.post("/api/hosts", base_url=BASE_URL, json={"hosts": hosts})
    assert client.post("/api/settings", base_url=BASE_URL, json=body).status_code == 200
    assert config.load_settings().contact_host == "Rakkos"


def test_save_post_day_and_time(client) -> None:
    body = {"post_day": "friday", "post_time": "18:30"}
    assert client.post("/api/settings", base_url=BASE_URL, json=body).status_code == 200
    state = client.get("/api/state", base_url=BASE_URL).json
    assert (state["post_day"], state["post_time"]) == ("friday", "18:30")
    assert state["next_post"].startswith("Friday, ")
    assert state["next_post"].endswith(" at 6:30 PM")


def test_bad_post_day_is_refused(client) -> None:
    response = client.post("/api/settings", base_url=BASE_URL, json={"post_day": "funday"})
    assert response.status_code == 400


def test_save_and_read_hosts(client) -> None:
    hosts = [{"name": "Blackeye", "discord_id": "123456789012345678"}]
    assert client.post("/api/hosts", base_url=BASE_URL, json={"hosts": hosts}).status_code == 200
    assert client.get("/api/state", base_url=BASE_URL).json["hosts"] == hosts


def test_bad_hosts_are_refused(client) -> None:
    hosts = [{"name": "A, B", "discord_id": "12"}]
    response = client.post("/api/hosts", base_url=BASE_URL, json={"hosts": hosts})
    assert response.status_code == 400
    assert "comma" in response.json["error"]
    assert not config.HOSTS_FILE.exists()
