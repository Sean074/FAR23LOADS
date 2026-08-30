"""A **native folder chooser**, for a GUI whose server is the user's own machine.

Streamlit has no directory picker, and a browser cannot hand a server-side
process a folder path -- ``st.file_uploader`` returns a file's *bytes* and never
its location. But the oracle GUI is run locally (OR-22: the user's machine *is*
the server), so the operating system's own dialog is reachable: run it in a
subprocess, let the user point at a folder, read the path back.

**Why a subprocess and not ``tkinter``.** Two reasons, either of which is
sufficient. This interpreter has no ``_tkinter`` at all, and on macOS Tk must run
on the main thread -- which a Streamlit script never does, so an in-process
dialog would abort the app rather than open. Shelling out sidesteps both, and
:mod:`sloads.export.pdf` is the standing precedent for an export-side helper that
runs an external program.

**Nothing here raises.** A machine with no dialog, a user who cancels, a hung
helper: all of them come back as ``None``, exactly as ``pdf.compile_pdf``
returns a result with no PDF rather than an exception. The caller always has the
in-app browser to fall back to, so a missing dialog must degrade rather than
break.

**It is not a permission grant.** On macOS, ``~/Desktop``, ``~/Documents`` and
``~/Downloads`` are TCC-protected: choosing one here does *not* give this process
access to it, because a plain interpreter is not a sandboxed app talking to the
powerbox. The dialog will happily return a folder that the subsequent write then
fails on, which is why every caller reports that failure as a message rather
than assuming a chosen folder is a usable one.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import List, Optional

#: How long to leave the dialog open before giving up on it.
#:
#: A folder chooser waits for a human, so this is not a "the command has failed"
#: timeout -- it is the point at which a dialog the user has walked away from
#: stops holding a Streamlit script thread. Generous on purpose.
DIALOG_TIMEOUT_S = 300


def _applescript_literal(path: str) -> str:
    """``path`` as an AppleScript string literal, quotes and backslashes escaped."""
    return path.replace("\\", "\\\\").replace('"', '\\"')


def _darwin_command(initial: str, prompt: str) -> List[str]:
    script = f'choose folder with prompt "{_applescript_literal(prompt)}"'
    if initial and os.path.isdir(initial):
        script += f' default location POSIX file "{_applescript_literal(initial)}"'
    return ["osascript", "-e", f"POSIX path of ({script})"]


def _windows_command(initial: str, prompt: str) -> List[str]:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog;"
        f"$d.Description = '{prompt}';"
        + (f"$d.SelectedPath = '{initial}';" if initial else "")
        + "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }"
    )
    return ["powershell", "-NoProfile", "-Command", script]


def _linux_command(initial: str, prompt: str) -> Optional[List[str]]:
    if shutil.which("zenity"):
        command = ["zenity", "--file-selection", "--directory",
                   f"--title={prompt}"]
        if initial:
            command.append(f"--filename={os.path.join(initial, '')}")
        return command
    if shutil.which("kdialog"):
        return ["kdialog", "--getexistingdirectory", initial or os.path.expanduser("~")]
    return None


def _command(initial: str, prompt: str) -> Optional[List[str]]:
    system = platform.system()
    if system == "Darwin":
        return _darwin_command(initial, prompt) if shutil.which("osascript") else None
    if system == "Windows":
        return _windows_command(initial, prompt) if shutil.which("powershell") else None
    return _linux_command(initial, prompt)


def native_picker_available() -> bool:
    """Whether this machine has a folder dialog we can drive.

    Asked *before* the button is drawn, so a machine without one shows the in-app
    browser instead of a control that does nothing when pressed.
    """
    return _command("", "") is not None


def choose_directory(initial: str = "", *,
                     prompt: str = "Choose a folder") -> Optional[str]:
    """Open the OS folder chooser and return the chosen path, or ``None``.

    ``None`` covers every non-answer alike -- no dialog on this machine, the user
    pressed Cancel, the helper timed out or failed -- because the caller's
    response to all four is the same: leave the current folder alone.
    """
    command = _command(initial, prompt)
    if command is None:
        return None
    try:
        finished = subprocess.run(command, capture_output=True, text=True,
                                  timeout=DIALOG_TIMEOUT_S, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    # Cancel is a non-zero exit on every one of these helpers, and is a normal
    # answer rather than a failure: the user was asked and said no.
    if finished.returncode != 0:
        return None
    chosen = finished.stdout.strip()
    if not chosen or not os.path.isdir(chosen):
        return None
    return os.path.abspath(chosen)


__all__ = ["DIALOG_TIMEOUT_S", "choose_directory", "native_picker_available"]
