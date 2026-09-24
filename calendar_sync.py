"""Google Calendar: sign in and read upcoming events.

Google Calendar is the source of truth. Deleted events need no special
handling: every run builds the schedule again from the current list of events.

Test the Google sign-in with: python calendar_sync.py

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

from config import CREDENTIALS_FILE, GOOGLE_SCOPES, TOKEN_FILE, load_settings


def get_credentials() -> Credentials:
    """Return valid Google credentials. Open a browser sign-in if necessary."""
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
        if not CREDENTIALS_FILE.exists():
            raise SystemExit(
                f"{CREDENTIALS_FILE} not found. Download the OAuth client (Desktop app) "
                "from Google Cloud and put it in the project folder."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), GOOGLE_SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    return creds


def list_upcoming_events(calendar_id: str, max_results: int = 10) -> list[dict]:
    """Return the next events from now, in start-time order."""
    service = build("calendar", "v3", credentials=get_credentials())
    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=datetime.now(UTC).isoformat(),
            maxResults=max_results,
            singleEvents=True,  # show each repeat of a recurring event
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
