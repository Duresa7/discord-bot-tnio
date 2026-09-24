"""Control panel: a local website for the friend who runs the bot.

Start: double-click "Start Control Panel.bat" (or: python -m tnio_bot.panel).
It listens on 127.0.0.1 only. See docs/SPEC.md, "Control panel".
"""

import asyncio
import functools
import logging
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, request, send_file

from tnio_bot import config, task
from tnio_bot.calendar_sync import MissingCredentials, get_credentials, sign_in_problem
from tnio_bot.hosts import host_row_errors, read_host_rows, write_host_rows
from tnio_bot.status import read_status
from tnio_bot.sync import friendly_error, preview_weeks, run_once, setup_logging

PORT = 8765
URL = f"http://localhost:{PORT}"
ALLOWED_HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}
PAGE = Path(__file__).with_name("panel.html")

log = logging.getLogger(__name__)
app = Flask(__name__)


class PanelError(RuntimeError):
    """An error with a message that is safe to show in the panel."""


@app.before_request
def only_this_computer():
    # Block other websites: a wrong Host header (DNS rebinding) or a foreign Origin.
    if request.host not in ALLOWED_HOSTS:
        abort(403)
    if request.method != "GET":
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc not in ALLOWED_HOSTS:
            abort(403)
        if not request.is_json:
            abort(415)


def api(view):
    """Return JSON, and change any error into ``{"error": "<plain words>"}``."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return jsonify(view(*args, **kwargs))
        except (PanelError, task.TaskError, MissingCredentials) as error:
            return jsonify(error=str(error)), 400
        except Exception as error:
            log.exception("Panel action failed")
            return jsonify(error=friendly_error(error)), 500

    return wrapper


@app.get("/")
def page():
    return send_file(PAGE)


@app.get("/api/state")
@api
def state():
    settings = config.load_settings()
    return {
        "status": read_status(config.STATUS_FILE),
        "server": settings.server,
        "servers": {
            name: {
                "channel_id": str(server.channel_id or ""),
                "emoji": server.emoji,
                "ping_everyone": server.ping_everyone,
            }
            for name, server in (("test", settings.test), ("real", settings.real))
        },
        "token_set": bool(settings.discord_token),
        "calendar_id": settings.google_calendar_id,
        "contact_host": settings.contact_host,
        "hosts": read_host_rows(config.HOSTS_FILE),
        "schedule_supported": task.supported(),
        "schedule_on": task.is_on(),
        "google_problem": sign_in_problem(),
    }


@app.post("/api/settings")
@api
def save_settings():
    body = request.get_json()
    updates = {}
    if "server" in body:
        if body["server"] not in config.SERVERS:
            raise PanelError("Unknown server.")
        updates["DISCORD_SERVER"] = body["server"]
    if "calendar_id" in body:
        updates["GOOGLE_CALENDAR_ID"] = body["calendar_id"].strip()
    if "contact_host" in body:
        contact = body["contact_host"].strip()
        known = {row["name"].casefold() for row in read_host_rows(config.HOSTS_FILE)}
        if contact and contact.casefold() not in known:
            raise PanelError(f"'{contact}' is not in the host list. Add the host first.")
        updates["CONTACT_HOST"] = contact
    if body.get("token", "").strip():
        updates["DISCORD_TOKEN"] = body["token"].strip()
    for name in config.SERVERS:
        if name not in body:
            continue
        server, prefix = body[name], name.upper()
        channel_id = str(server.get("channel_id", "")).strip()
        if channel_id and not channel_id.isdigit():
            raise PanelError(f"The {name} channel ID must contain only digits.")
        updates[f"{prefix}_CHANNEL_ID"] = channel_id
        updates[f"{prefix}_SCHEDULE_EMOJI"] = str(server.get("emoji", "")).strip()
        updates[f"{prefix}_PING_EVERYONE"] = "true" if server.get("ping_everyone") else "false"
    _ensure_env_file()
    config.update_env_file(config.ENV_FILE, updates)
    return {"saved": True}


@app.post("/api/hosts")
@api
def save_hosts():
    rows = [
        {"name": str(row.get("name", "")), "discord_id": str(row.get("discord_id", ""))}
        for row in request.get_json().get("hosts", [])
    ]
    errors = host_row_errors(rows)
    if errors:
        raise PanelError(" ".join(errors))
    write_host_rows(config.HOSTS_FILE, rows)
    return {"saved": True}


@app.get("/api/preview")
@api
def preview():
    settings = config.load_settings()
    weeks, members, note = asyncio.run(preview_weeks(settings, get_credentials(interactive=False)))
    # Names for the blue mentions in the preview: the server name, else the host-list name.
    names = {row["discord_id"]: row["name"] for row in read_host_rows(config.HOSTS_FILE)}
    names.update({str(member.id): member.display for member in members})
    return {
        "server": settings.server,
        "note": note,
        "names": names,
        "weeks": [
            {"title": f"Week of {start:%B} {start.day}", "messages": list(messages.contents)}
            for start, messages in weeks
        ],
    }


@app.post("/api/sync")
@api
def sync_now():
    status = run_once()
    if not status["ok"]:
        raise PanelError(status["error"])
    return status


@app.post("/api/signin")
@api
def sign_in():
    get_credentials(interactive=True)  # opens the Google sign-in in the browser
    return {"signed_in": True}


@app.post("/api/schedule")
@api
def set_schedule():
    if request.get_json().get("on"):
        task.turn_on()
    else:
        task.turn_off()
    return {"schedule_on": task.is_on()}


@app.post("/api/update")
@api
def update():
    if shutil.which("git") is None:
        raise PanelError("Git is not installed. Run Install.bat again.")
    output = []
    for command in (
        ["git", "pull", "--ff-only"],
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q",
         "-r", "requirements.txt"],
    ):  # fmt: skip
        result = subprocess.run(
            command, cwd=config.BASE_DIR, capture_output=True, text=True,
            creationflags=task.NO_WINDOW,
        )  # fmt: skip
        output.append(f"> {' '.join(command[:3])}\n{result.stdout}{result.stderr}".strip())
        if result.returncode != 0:
            raise PanelError("The update failed:\n\n" + "\n\n".join(output))
    return {"output": "\n\n".join(output)}


def _ensure_env_file() -> None:
    if not config.ENV_FILE.exists() and config.ENV_EXAMPLE_FILE.exists():
        shutil.copyfile(config.ENV_EXAMPLE_FILE, config.ENV_FILE)


def _already_running() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", PORT)) == 0


def main() -> None:
    if _already_running():
        print(f"The control panel is already running: {URL}")
        webbrowser.open(URL)
        return
    setup_logging()
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    print(f"Control panel: {URL}")
    print("Keep this window open. Close it to stop the panel (the bot schedule continues).")
    threading.Timer(1.0, webbrowser.open, [URL]).start()
    app.run(host="127.0.0.1", port=PORT, threaded=True)


if __name__ == "__main__":
    main()
