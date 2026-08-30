- **The saved-projects list no longer crashes on an unreadable folder.**
  `list_saved_projects` guarded a *missing* projects directory but not one that
  exists and cannot be read, so a projects folder in a macOS TCC-protected
  location (`~/Desktop`, `~/Documents`, `~/Downloads`) raised `PermissionError`
  straight through the sidebar render. A directory this process cannot read now
  reports as holding no projects, which is the question the sidebar is asking.
