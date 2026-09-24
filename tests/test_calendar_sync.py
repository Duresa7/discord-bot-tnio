from calendar_sync import format_event, to_event


def test_to_event_timed() -> None:
    item = {
        "summary": " Force Pantheon (F) ",
        "start": {"dateTime": "2026-09-22T04:00:00Z"},
        "description": "Host: Kaelis",
    }
    event = to_event(item)
    assert event.title == "Force Pantheon (F)"
    assert (event.start.day, event.start.hour) == (22, 0)  # 12:00 AM Eastern
    assert event.hosts == ("Kaelis",)


def test_to_event_skips_all_day_and_cancelled() -> None:
    assert to_event({"summary": "XP Weekend", "start": {"date": "2026-09-26"}}) is None
    cancelled = {"status": "cancelled", "start": {"dateTime": "2026-09-22T20:00:00-04:00"}}
    assert to_event(cancelled) is None


def test_format_timed_event() -> None:
    event = {"summary": "Practice", "start": {"dateTime": "2026-09-25T16:00:00-04:00"}}
    assert format_event(event) == "Fri Sep 25, 4:00 PM - Practice"


def test_format_all_day_event() -> None:
    event = {"summary": "Tournament", "start": {"date": "2026-09-27"}}
    assert format_event(event) == "Sun Sep 27 (all day) - Tournament"
