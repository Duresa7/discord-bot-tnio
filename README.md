# discord-bot-tnio

A Discord bot that posts the weekly event schedule from a Google Calendar and
keeps it up to date. Google Calendar is the source of truth.

- Each **Sunday at 9:00 PM Eastern**, the bot posts 3 messages with the next week's events.
- During the week, it **edits** those messages when the calendar changes.
- Events that start before 5:00 AM show under the day before.

The full rules are in [docs/SPEC.md](docs/SPEC.md).

```
Google Calendar → Google Calendar API → bot.py (Windows PC) → Discord API → 3 schedule messages
```

## 1. Install (Windows)

Install Python 3.11 or later from [python.org](https://www.python.org/downloads/).
Then, in the project folder:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## 2. Google sign-in

1. Put `credentials.json` (the OAuth client, Desktop app type) in the project folder.
2. In Google Cloud → Google Auth Platform → Audience, add the Google account as a test user.
3. Run `python bot.py --sign-in`. A browser opens. Sign in and allow read-only access.

This makes `token.json` and prints the next 10 events.

> In "Testing" mode, Google ends the sign-in after 7 days. Before the bot runs
> all the time, click **Publish app** under Audience.

Set `GOOGLE_CALENDAR_ID` in `.env` to the shared calendar's ID.

## 3. Discord bot

1. In the [Discord Developer Portal](https://discord.com/developers/applications), make an application. On the **Bot** page, copy the token into `.env` as `DISCORD_TOKEN`.
2. Invite the bot to the server with these permissions: **View Channel**, **Send Messages**, **Read Message History**, **Mention Everyone**. No privileged intents are necessary.
3. In Discord, turn on Developer Mode. Right-click the schedule channel → **Copy Channel ID**. Put it in `.env` as `DISCORD_CHANNEL_ID`.
4. Optional: `PING_EVERYONE=true` and `SCHEDULE_EMOJI=<:name:id>` (type `\:name:` in Discord to get the emoji code).

## 4. Hosts

A calendar event can name its host(s) in the description:

```
Host: Blackeye, Gonnmakh
```

[data/hosts.csv](data/hosts.csv) changes each short name to a Discord user ID, so the bot
can show a clickable mention (the host gets no notification):

```
name,discord_id
Blackeye,123456789012345678
```

To get an ID: Developer Mode on → right-click the user → **Copy User ID**.
A name that is not in the list shows as plain text.

## 5. Test

```powershell
python bot.py --preview   # print the messages; nothing goes to Discord
python bot.py             # sync the Discord channel one time
```

## 6. Run every 5 minutes

```powershell
.\scripts\install_task.ps1
```

This registers the Windows Task Scheduler task "Discord Calendar Bot". It runs
while the user is signed in to Windows. Messages and errors go to `bot.log`.

## Secret files

These files stay on the computer only. `.gitignore` blocks them. Never commit them.

| File | What it is |
| --- | --- |
| `.env` | Discord token, channel ID, calendar ID |
| `credentials.json` | Google OAuth client, downloaded from Google Cloud |
| `token.json` | Made on the first Google sign-in |

## Development

```powershell
pip install -r requirements-dev.txt
pytest
ruff check .
ruff format .
```

## Folder layout

```
discord-bot-tnio/
├── bot.py                  # the only entry point: sync, --preview, --sign-in
├── tnio_bot/               # application code
│   ├── config.py           #   settings from .env, file paths
│   ├── schedule.py         #   builds the 3 message texts (no network)
│   ├── discord_sync.py     #   finds, posts, edits, and reposts the messages
│   ├── calendar_sync.py    #   Google sign-in and event reads
│   └── hosts.py            #   "Host:" lines and hosts.csv
├── data/
│   └── hosts.csv           # host name -> Discord user ID
├── docs/
│   └── SPEC.md             # the agreed design
├── scripts/
│   └── install_task.ps1    # registers the 5-minute scheduled task
├── tests/                  # pytest tests, one file for each module
├── .env.example            # copy to .env (local only)
├── requirements.txt        # runtime libraries
├── requirements-dev.txt    # + pytest and ruff
└── pyproject.toml          # pytest and ruff settings
```

Local only (git ignores them): `.env`, `credentials.json`, `token.json`, `bot.log`, `.venv/`.
