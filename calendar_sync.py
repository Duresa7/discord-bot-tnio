"""Google Calendar: sign in and read events.

Google Calendar is the source of truth. Deleted events need no special
handling: every run builds the schedule again from the current list of events.

Sign in (or test the sign-in) with: python calendar_sync.py

The first run opens a browser for Google sign-in and makes ``token.json``.
Later runs use ``token.json``. Both ``credentials.json`` and ``token.json``
stay local and are never committed.
"""

from datetime import UTC, datetime

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import CREDENTIALS_FILE, EASTERN, GOOGLE_SCOPES, TOKEN_FILE, load_settings
from hosts import parse_host_names
from schedule import Event


class SignInRequired(RuntimeError):
    """Google sign-in is necessary, but this run must not open a browser."""


def get_credentials(interactive: bool = True) -> Credentials:
    """Return valid Google credentials.

    If a new sign-in is necessary, open a browser when ``interactive`` is true,
    else raise ``SignInRequired``.
    """
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GOOGLE_SCOPES)
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # Revoked, or expired (apps in "Testing" mode expire after 7 days).
            creds = None
    else:
        creds = None

    if creds is None:
        if not interactive:
            raise SignInRequired("Google sign-in is necessary. Run: python calendar_sync.py")
        if not CREDENTIALS_FILE.exists():
            raise SystemExit(
                f"{CREDENTIALS_FILE.name} not found. Download the OAuth client (Desktop app) "
                "from Google Cloud and put it in the project folder."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GOOGLE_SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    return creds


def _service(creds: Credentials):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def fetch_week_events(
    creds: Credentials, calendar_id: str, start: datetime, end: datetime
) -> list[Event]:
    """Return the timed events that start from ``start`` up to (not including) ``end``."""
    events = []
    resource = _service(creds).events()
    request = resource.list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,  # show each repeat of a recurring event
        orderBy="startTime",
        maxResults=2500,
    )
    while request is not None:
        response = request.execute()
        for item in response.get("items", []):
            event = to_event(item)
            # Google also returns events that started earlier but end inside the range.
            if event and start <= event.start < end:
                events.append(event)
        request = resource.list_next(request, response)
    return events


def to_event(item: dict) -> Event | None:
    """Change one Google Calendar item into an ``Event``. All-day and cancelled events give None."""
    if item.get("status") == "cancelled" or "dateTime" not in item.get("start", {}):
        return None
    return Event(
        title=item.get("summary", "(no title)").strip(),
        start=datetime.fromisoformat(item["start"]["dateTime"]).astimezone(EASTERN),
        hosts=parse_host_names(item.get("description")),
    )


def list_upcoming_events(calendar_id: str, max_results: int = 10) -> list[dict]:
    """Return the next events from now, in start-time order."""
    result = (
        _service(get_credentials())
        .events()
        .list(
            calendarId=calendar_id,
            timeMin=datetime.now(UTC).isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def format_event(event: dict) -> str:
    """Format one event as a line, for example ``Thu Sep 25, 4:00 PM - Practice``."""
    title = event.get("summary", "(no title)")
    start = event["start"]
    if "dateTime" in start:
        when = datetime.fromisoformat(start["dateTime"])
        hour = f"{when:%I:%M %p}".lstrip("0")
        return f"{when:%a %b} {when.day}, {hour} - {title}"
    day = datetime.fromisoformat(start["date"])
    return f"{day:%a %b} {day.day} (all day) - {title}"


def main() -> None:
    settings = load_settings()
    events = list_upcoming_events(settings.google_calendar_id)
    if not events:
        print("No upcoming events.")
    for event in events:
        print(format_event(event))


if __name__ == "__main__":
    main()
