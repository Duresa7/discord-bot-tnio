"""Windows Task Scheduler: turn the 5-minute bot task on and off."""

import subprocess
import sys

from tnio_bot import config

TASK_NAME = "Discord Calendar Bot"  # same name as in scripts/install_task.ps1
INSTALL_SCRIPT = config.BASE_DIR / "scripts" / "install_task.ps1"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no black window flashes


class TaskError(RuntimeError):
    """A Task Scheduler command failed. The message is safe to show in the panel."""


def supported() -> bool:
    return sys.platform == "win32"


def is_on() -> bool:
    if not supported():
        return False
    query = ["schtasks", "/Query", "/TN", TASK_NAME]
    return subprocess.run(query, capture_output=True, creationflags=NO_WINDOW).returncode == 0


def turn_on() -> None:
    # Bypass applies to this one PowerShell process only; no system setting changes.
    _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INSTALL_SCRIPT)])


def turn_off() -> None:
    _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])


def _run(command: list[str]) -> None:
    if not supported():
        raise TaskError("The 5-minute schedule works on Windows only.")
    result = subprocess.run(command, capture_output=True, text=True, creationflags=NO_WINDOW)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise TaskError(f"Task Scheduler did not accept the change. {detail}".strip())
