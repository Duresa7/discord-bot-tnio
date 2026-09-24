# Weekly schedule: spec

Agreed with the project owner on 2026-09-24.

## Goal

Each week, the bot posts the event schedule for that week in one Discord
channel. During the week, it edits the same messages when the Google Calendar
changes. Google Calendar is the source of truth.

## Terms

| Term | Meaning |
| --- | --- |
| **Eastern time** | `America/New_York`. EST or EDT is applied automatically. The header always says "EST". |
| **Late-night cutoff** | 5:00 AM Eastern. An event that starts before the cutoff belongs to the day before. |
| **Schedule day** | A calendar date plus its late-night events. Tuesday = Tue 5:00 AM to Wed 4:59 AM. |
| **Schedule week** | Monday 5:00 AM to the next Monday 5:00 AM (Eastern). |
| **Post time** | Sunday 9:00 PM Eastern. From this time, the next week is also posted. |
| **Week messages** | The 3 bot messages for one schedule week. |
| **Host list** | `data/hosts.csv`: short host name → Discord user ID. |

## Source events

- Calendar: `GOOGLE_CALENDAR_ID` (the shared calendar that the friend's account can see).
- Show every event that has a start time and starts inside the schedule week.
- Skip all-day events.

## Week messages

| Message | Contents |
| --- | --- |
| 1 | `@everyone` line (only if `PING_EVERYONE=true`), header, Monday, Tuesday |
| 2 | Wednesday, Thursday, Friday |
| 3 | Saturday, Sunday |

Header (same text as the manual schedule; `<emoji>` comes from `SCHEDULE_EMOJI`, empty = none):

```
**EVENT SCHEDULE FOR THE WEEK OF SEPTEMBER 21ST - SEPTEMBER 27TH**
[ LATE NIGHT EVENTS APPEAR ON PRIOR DATE ]

*Story events will be annotated with the following abbreviations for clarity*
[O] open to everyone
[I] characters initiated to any faction
[A+] Apprentice and up
[F] faction members only

<emoji> **ALL TIMES IN EST** <emoji>
```

Each day:

```
**MONDAY, SEPTEMBER 21ST**
- 8:00 PM - Praetorian Training - @Blackeye
- 12:00 AM - Force Pantheon (F) - @Kaelis
```

- Events are in start-time order. A line shows the start time only.
- The title is copied exactly (tags such as `(F)` or `INQ:` come from the title).
- A day with no events shows its heading and `- No events`.

### Hosts

- The event description has a line `Host: Blackeye, Gonnmakh` (comma list; `Hosts:` also works; case does not matter).
- A name in the host list becomes a mention `<@id>`. The mention does not notify the user.
- A name not in the list shows as plain text, and the bot logs a warning.
- No `Host:` line = no host part on the line.

### Overflow (a message over 2,000 characters)

1. Build that message again without the host parts.
2. If it is still too long, remove event lines from the end until it fits, and
   add `- … more events: see the calendar`. Log a warning.

## Timing

- Windows Task Scheduler starts `bot.py` every 5 minutes. Each run syncs and then stops.
- Active weeks at run time:
  - the current schedule week, always;
  - the next schedule week, from the post time (Sunday 9:00 PM).
- The old week stays active until Monday 5:00 AM, so late Sunday changes still show.

## Sync of one active week

The bot finds its own messages in the channel, posted after the week's post
time minus 1 hour. It identifies each message by a marker: message 1 by the
week title, messages 2 and 3 by their first day heading.

| Found | Action |
| --- | --- |
| All 3 | Edit each message whose text changed. No change = no API call. |
| None | Post all 3. Message 1 pings `@everyone` if `PING_EVERYONE=true`. |
| 1 or 2 (somebody deleted one) | Delete the ones found, then post all 3 again. No `@everyone` ping. |

Mentions never notify anyone on an edit or a repost.

## Configuration (`.env`)

| Key | Meaning |
| --- | --- |
| `DISCORD_TOKEN` | Bot token |
| `DISCORD_CHANNEL_ID` | Schedule channel |
| `PING_EVERYONE` | `true` / `false` (default `false`) |
| `SCHEDULE_EMOJI` | Emoji around "ALL TIMES IN EST", for example `<:tnio:123>` |
| `GOOGLE_CALENDAR_ID` | Calendar to read (default `primary`) |

Test server → real server: change `DISCORD_CHANNEL_ID` and `SCHEDULE_EMOJI`.

## Discord permissions

View Channel, Send Messages, Read Message History, Mention Everyone.
No privileged intents.

## Failure behavior

- Scheduled runs never open a browser. If Google sign-in is necessary, the run
  logs an error and stops. Fix: run `python bot.py --sign-in` by hand.
- Errors go to `bot.log` in the project folder.
