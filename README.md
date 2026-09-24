# discord-bot-tnio

A Discord bot that posts the weekly event schedule from a Google Calendar and
keeps it up to date. Google Calendar is the source of truth.

- Each **Sunday at 9:00 PM Eastern**, the bot posts 3 messages with the next week's events.
- During the week, it **edits** those messages when the calendar changes.
- Events that start before 5:00 AM show under the day before.

The full rules are in [docs/SPEC.md](docs/SPEC.md).

```
Google Calendar → Google Calendar API → bot (Windows PC) → Discord API → 3 schedule messages
```

## Quick start (no terminal)

1. Install **Python** from [python.org](https://www.python.org/downloads/). In the installer, check **"Add python.exe to PATH"**.
2. On GitHub, click **Code → Download ZIP**. Unzip it to a folder, for example `Documents\Schedule Bot`.
3. Double-click **`Install.bat`**. It installs everything (also Git, if it is missing). If it asks you to run it again, do that.
4. Put **`credentials.json`** in the folder.
5. Double-click **`Start Control Panel.bat`**. The control panel opens in your browser.

In the control panel:

1. **Settings:** paste the Discord bot token and the Google Calendar ID.
2. Click **Sign in to Google** and sign in with the account that can see the calendar.
3. **Discord server:** type the test channel ID. Click **Save server settings**.
4. **Hosts:** add each host's name and Discord user ID.
5. Look at the **Preview**. If it is correct, click **Sync now**.
6. **Bot schedule:** click **Turn on**. The bot now runs every 5 minutes, also when the panel is closed.
7. When the test works, switch **Discord server** to **Real server**.

To get a new version later, click **Update the bot**, then start the panel again.

## One-time setup (bot owner)

### Google

1. Put `credentials.json` (the OAuth client, Desktop app type) in the project folder.
2. In Google Cloud → Google Auth Platform → Audience, add each Google account that signs in as a test user.
3. Sign in with the panel's button, or run `python bot.py --sign-in`.

> In "Testing" mode, Google ends the sign-in after 7 days. Before the bot runs
> all the time, click **Publish app** under Audience.

### Discord

1. In the [Discord Developer Portal](https://discord.com/developers/applications), make an application. On the **Bot** page, copy the token.
2. Invite the bot to the test server and the real server with these permissions: **View Channel**, **Send Messages**, **Read Message History**, **Mention Everyone**. No privileged intents are necessary.
3. In Discord, turn on Developer Mode. Right-click the schedule channel → **Copy Channel ID**.
4. Emoji code (optional): type `\:name:` in Discord and copy the result, for example `<:tnio:123456789012345678>`.

## Hosts

A calendar event can name its host(s) in the description:

```
Host: Blackeye, Gonnmakh
```

The host list (panel → **Hosts**, saved in the local file `data/hosts.csv`)
changes each name to a Discord user ID, so the bot can show a clickable
mention. The host gets no notification. A name that is not in the list shows
as plain text.

## Command line (optional)

```powershell
python bot.py              # sync the Discord channel one time
python bot.py --preview    # print the messages; nothing goes to Discord
python bot.py --sign-in    # Google sign-in, then print the next 10 events
python -m tnio_bot.panel   # start the control panel
.\scripts\install_task.ps1 # turn on the 5-minute schedule
```

## Local files

Git ignores these files. They stay on the bot PC only. Never commit them.

| File | What it is |
| --- | --- |
| `.env` | Bot token, server settings, calendar ID |
| `credentials.json` | Google OAuth client, downloaded from Google Cloud |
| `token.json` | Made on the first Google sign-in |
| `data/hosts.csv` | Host list |
| `status.json`, `bot.log` | Last run result, and the log |

## Development

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
ruff check .
ruff format .
```

## Folder layout

```
discord-bot-tnio/
├── Install.bat               # one-click install (the friend's first step)
├── Start Control Panel.bat   # opens the control panel
├── bot.py                    # entry point for the scheduled task: sync, --preview, --sign-in
├── tnio_bot/                 # application code
│   ├── panel.py / panel.html #   control panel (local website)
│   ├── sync.py               #   one sync run (used by bot.py and the panel)
│   ├── schedule.py           #   builds the 3 message texts (no network)
│   ├── discord_sync.py       #   finds, posts, edits, and reposts the messages
│   ├── calendar_sync.py      #   Google sign-in and event reads
│   ├── hosts.py              #   "Host:" lines and the host list
│   ├── task.py               #   Task Scheduler on/off
│   ├── status.py             #   status.json and the sync lock
│   └── config.py             #   settings from .env, file paths
├── data/
│   └── hosts.example.csv     # empty host list (Install.bat copies it to hosts.csv)
├── docs/
│   └── SPEC.md               # the agreed design
├── scripts/
│   └── install_task.ps1      # registers the 5-minute scheduled task
├── tests/                    # pytest tests
├── .env.example              # settings template (Install.bat copies it to .env)
├── requirements.txt          # runtime libraries
├── requirements-dev.txt      # + pytest and ruff
└── pyproject.toml            # pytest and ruff settings
```
