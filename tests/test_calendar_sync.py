from calendar_sync import format_event


def test_timed_event() -> None:
    event = {"summary": "Practice", "start": {"dateTime": "2026-09-25T16:00:00-04:00"}}
    assert format_event(event) == "Fri Sep 25, 4:00 PM - Practice"


def test_all_day_event() -> None:
    event = {"summary": "Tournament", "start": {"date": "2026-09-27"}}
    assert format_event(event) == "Sun Sep 27 (all day) - Tournament"


def test_event_without_title() -> None:
    event = {"start": {"dateTime": "2026-09-26T18:30:00-04:00"}}
    assert format_event(event) == "Sat Sep 26, 6:30 PM - (no title)"
