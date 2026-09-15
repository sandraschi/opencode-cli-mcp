# Sidebar companion (AHK desktop overlay)

Old-school session sidebar for the opencode desktop app, replacing the top-tab chaos
with a docked list. Lives in `sidebar/` and ships **outside** the `.mcpb`
(see `.mcpbignore`) — it is a Windows companion client, not MCP payload.

## Files

| File | Purpose |
|------|---------|
| `sidebar/opencode-sidebar.ahk` | Tray script (AHK v2): docked panel, tooltips, menus, guards |
| `sidebar/sidebar_client.py` | Thin TSV CLI over `opencode_cli_mcp.depot` (no raw SQL) |

## Run

Double-click `sidebar/opencode-sidebar.ahk` (needs AHK v2). Autostart: drop a shortcut
in `shell:startup` targeting the AHK exe plus this script.

Toggle the panel with `Ctrl+Alt+O` while the opencode desktop window (`OpenCode.exe`)
is active.

## What it does

- Session list with Title / Model (`provider/id`) / Updated / Cost / Mark columns,
  backed by the depot `list_sessions` path (active sessions, newest first).
- Jump-to-session via the desktop command palette (`Ctrl+K`, Sessions category).
- New-session-here via the `opencode://new-session` deep link.
- Right-click: Rename, Archive, **Delete** (MsgBox confirm + depot FK cascade +
  backup rotation), Undo via backups, Star / Rate / Comment (local `sidecar.ini`,
  Mark column), Copy session id.
- Hover any row: wrapped chat-tail tooltip (YOU/AI, from depot transcripts).
- Preview pane under the list: selectable tail of the focused session.
- Filter box, star-only toggle, Cost/Title header sort, footer totals,
  60s auto-refresh, left/right dock toggle.
- Guards: truthful tab-strip tooltip (X closes the tab only), `AppsKey` menu,
  middle-click swallow over the strip.

## Data & safety

- All reads/writes go through `opencode_cli_mcp.depot` (narrow update path,
  `PRAGMA foreign_keys = ON`, busy timeout). No ad-hoc SQL against the 9GB depot.
- Mutations are covered by the `opencode_backups` rotation; there is no in-band
  undo because restore is the supported path.
- `sidecar.ini` (stars/ratings/comments) and scratch TSVs live outside the repo
  (`%TEMP%\opencode\`) and are never committed.
