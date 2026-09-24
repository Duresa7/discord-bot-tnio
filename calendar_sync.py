"""Google Calendar synchronization (placeholder).

This module will be implemented later. Google Calendar is the source of
truth. The plan:

1. Authenticate with OAuth (Desktop app client). The OAuth client file is
   ``credentials.json``. The first sign-in creates ``token.json``. Both files
   stay local and are never committed.
2. Read upcoming events (for example the next 7, 14, or 30 days) from
   ``GOOGLE_CALENDAR_ID``. The value ``primary`` means the primary calendar of
   the Google account that signed in.
3. Format the events as the schedule text.

Deleted events need no special handling: every run builds the schedule again
from the current list of events.
"""
