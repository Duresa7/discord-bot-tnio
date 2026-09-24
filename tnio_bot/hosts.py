"""Hosts: read ``Host:`` lines from event descriptions, and change names to Discord mentions."""

import csv
import html
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

_HOST_LINE = re.compile(r"^\s*hosts?\s*:\s*(.*)$", re.IGNORECASE | re.MULTILINE)
_LINE_BREAK_TAG = re.compile(r"<br\s*/?>|</p>|</div>|</li>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def parse_host_names(description: str | None) -> tuple[str, ...]:
    """Return the names in the first ``Host:`` line, for example ``("Blackeye", "Gonnmakh")``.

    Google Calendar can store the description as HTML, so tags are removed first.
    """
    if not description:
        return ()
    text = html.unescape(_TAG.sub("", _LINE_BREAK_TAG.sub("\n", description)))
    match = _HOST_LINE.search(text)
    if not match:
        return ()
    names = (name.strip().lstrip("@").strip() for name in match.group(1).split(","))
    return tuple(name for name in names if name)


def load_hosts(path: Path) -> dict[str, int]:
    """Read ``hosts.csv`` (columns ``name,discord_id``). Keys are case-folded names."""
    if not path.exists():
        log.warning("%s not found: no host mentions.", path.name)
        return {}
    hosts = {}
    with path.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            name = (row.get("name") or "").strip()
            user_id = (row.get("discord_id") or "").strip()
            if not name:
                continue
            if not user_id.isdigit():
                log.warning("%s: %r has no valid Discord user ID.", path.name, name)
                continue
            hosts[name.casefold()] = int(user_id)
    return hosts


def read_host_rows(path: Path) -> list[dict[str, str]]:
    """Return the rows of ``hosts.csv`` as written, for the panel's table."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as file:
        return [
            {
                "name": (row.get("name") or "").strip(),
                "discord_id": (row.get("discord_id") or "").strip(),
            }
            for row in csv.DictReader(file)
            if (row.get("name") or "").strip()
        ]


def host_row_errors(rows: list[dict[str, str]]) -> list[str]:
    """Return one message for each problem in ``rows``. An empty list means the rows are valid."""
    errors, seen = [], set()
    for number, row in enumerate(rows, start=1):
        name = row.get("name", "").strip()
        user_id = row.get("discord_id", "").strip()
        if not name:
            errors.append(f"Row {number}: the name is empty.")
        elif "," in name:
            errors.append(f"Row {number}: a name cannot contain a comma.")
        elif name.casefold() in seen:
            errors.append(f"Row {number}: '{name}' is in the list two times.")
        seen.add(name.casefold())
        if not (user_id.isdigit() and 15 <= len(user_id) <= 20):
            errors.append(f"Row {number}: the Discord user ID must be 15 to 20 digits.")
    return errors


def write_host_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "discord_id"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"name": row["name"].strip(), "discord_id": row["discord_id"].strip()})


def host_text(name: str, hosts: dict[str, int]) -> str:
    """Return a mention ``<@id>`` for a known host, else the plain name."""
    user_id = hosts.get(name.casefold())
    return f"<@{user_id}>" if user_id else name
