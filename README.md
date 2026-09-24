# discord-bot-tnio

A Discord bot that keeps one schedule message synchronized with a Google
Calendar. Google Calendar is the source of truth: the bot reads the upcoming
events every few minutes and edits the same Discord message.

> **Status:** scaffold only. The bot does not do anything yet.

```
Google Calendar → Google Calendar API → Python app (Windows PC) → Discord Bot API → schedule message
```

## Setup (Windows)

Install Python 3.11 or later from [python.org](https://www.python.org/downloads/).
Then, in the project folder:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python bot.py
```

Put your own values in `.env`.

## Secret files

These files stay on your computer only. `.gitignore` blocks them. Never commit them.

| File | What it is |
| --- | --- |
| `.env` | Discord token, channel ID, message ID, calendar ID |
| `credentials.json` | Google OAuth client (Desktop app), downloaded from Google Cloud |
| `token.json` | Made on the first Google sign-in |

The Google account that signs in decides which calendar the bot reads.
Access is read-only (`calendar.readonly`).

## Test the Google sign-in

1. Put `credentials.json` in the project folder.
2. In Google Cloud → Google Auth Platform → Audience, add the Google account as a test user.
3. Run `python calendar_sync.py`. A browser opens. Sign in and allow access.

The script makes `token.json` and prints your next 10 events. Later runs do not open the browser.

## Development

```powershell
pip install -r requirements-dev.txt
pytest
ruff check .
ruff format .
```

## Files

| File | Purpose |
| --- | --- |
| `bot.py` | Entry point (placeholder) |
| `calendar_sync.py` | Google Calendar sync (placeholder) |
| `config.py` | Settings from environment variables |
| `tests/` | pytest tests |

## Roadmap

1. Repository and scaffold (done)
2. Sign in to Google on the Windows PC and print upcoming events
3. Connect Discord and keep the schedule message synchronized
