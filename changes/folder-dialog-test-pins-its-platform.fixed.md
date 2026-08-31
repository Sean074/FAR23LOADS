- **The folder-dialog test no longer asserts the host's own dialog helpers (tier S, 2026-08-31).**
  `test_the_folder_dialog_never_raises_and_never_invents_a_path` stubbed the
  subprocess but not the command resolution, so it read whichever helper the
  machine running it happened to have. `choose_directory` returns `None` before it
  runs anything when the platform has none, and the CI runner has neither `zenity`
  nor `kdialog` — so the first case failed there while passing on every developer
  Mac. The four non-answers it covers are decisions made *after* the helper runs,
  so the helper has to exist for them to be reachable; the platform is now pinned
  alongside the subprocess. `sloads/export/directory_dialog.py` is unchanged: its
  behaviour on a machine with no dialog was correct, and is what the sibling test
  pins from the other side.
