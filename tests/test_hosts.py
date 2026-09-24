from tnio_bot.hosts import (
    host_row_errors,
    host_text,
    load_hosts,
    parse_host_names,
    read_host_rows,
    write_host_rows,
)


def test_write_and_read_rows(tmp_path) -> None:
    path = tmp_path / "data" / "hosts.csv"
    rows = [{"name": "Blackeye", "discord_id": "123456789012345678"}]
    write_host_rows(path, rows)
    assert read_host_rows(path) == rows
    assert load_hosts(path) == {"blackeye": 123456789012345678}


def test_host_row_errors() -> None:
    good = {"name": "Blackeye", "discord_id": "123456789012345678"}
    assert host_row_errors([good]) == []
    errors = host_row_errors(
        [good, {"name": "blackeye", "discord_id": "1"}, {"name": "", "discord_id": "x"}]
    )
    assert errors == [
        "Row 2: 'blackeye' is in the list two times.",
        "Row 2: the Discord user ID must be 15 to 20 digits.",
        "Row 3: the name is empty.",
        "Row 3: the Discord user ID must be 15 to 20 digits.",
    ]


def test_plain_host_line() -> None:
    assert parse_host_names("Bring gear\nHost: Blackeye, Gonnmakh\n") == ("Blackeye", "Gonnmakh")


def test_hosts_plural_case_and_at_sign() -> None:
    assert parse_host_names("HOSTS: @Blackeye ,  @Gonnmakh") == ("Blackeye", "Gonnmakh")


def test_html_description() -> None:
    description = "<b>Host:</b> Khonsu &amp; Co<br>Bring gear"
    assert parse_host_names(description) == ("Khonsu & Co",)


def test_no_host_line() -> None:
    assert parse_host_names("Bring gear") == ()
    assert parse_host_names(None) == ()


def test_load_hosts(tmp_path) -> None:
    path = tmp_path / "hosts.csv"
    path.write_text("name,discord_id\nBlackeye,111\nBad,abc\n,222\n", encoding="utf-8")
    assert load_hosts(path) == {"blackeye": 111}


def test_missing_hosts_file(tmp_path) -> None:
    assert load_hosts(tmp_path / "hosts.csv") == {}


def test_host_text() -> None:
    hosts = {"blackeye": 111}
    assert host_text("BlackEye", hosts) == "<@111>"
    assert host_text("Vistenia", hosts) == "Vistenia"
