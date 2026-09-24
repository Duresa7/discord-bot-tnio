from hosts import host_text, load_hosts, parse_host_names


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
