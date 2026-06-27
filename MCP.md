# MiniTask MCP Server — Tool Reference

The MiniTask MCP server (`mcp_server.py`) exposes your CalDAV tasks to any
MCP-compatible AI client (Claude Code, Claude Desktop, Cowork, …) so you can
manage them in natural language.

For installation and credential setup, see the
[MCP Server section in the README](README.md#mcp-server-claude-code-integration).
This document is the detailed reference for the tools themselves.

## Concepts

- **Tasks live on a CalDAV server** as `VTODO` items. The MCP server connects
  on first use, reading credentials from the system keyring (or a local
  `minitask_profile.ini`). No separate service to start — the client launches it
  as a subprocess.
- **`uri`** is the stable handle for a task. Always obtain it from `list_tasks`
  before updating or completing a task.
- **Stars** map to the iCalendar `PRIORITY:1` property. A starred task has
  `starred: true`.
- **Completing a task deletes it** from the server — exactly like checking it
  off in the desktop app. There is no separate "done" list.
- **Dates** are plain `YYYY-MM-DD` strings (the `DUE` date), with no time
  component.

## Tools

### `list_tasks`

List all open (incomplete) tasks in the current calendar.

- **Parameters:** none
- **Returns:** a list of task objects:

  | Field | Type | Notes |
  |---|---|---|
  | `id` | string | UID of the task |
  | `uri` | string | Stable handle — pass to `update_task` / `complete_task` |
  | `title` | string | Task summary |
  | `date` | string | Due date `YYYY-MM-DD`, or `""` if none |
  | `starred` | bool | `true` = `PRIORITY:1` set |
  | `completed` | bool | Always `false` here (completed tasks aren't listed) |

### `create_task`

Create a new task.

- **Parameters:**
  - `title` (string, required) — the task summary
  - `date` (string, optional) — due date `YYYY-MM-DD`; **defaults to today** if omitted
- **Returns:** confirmation string

### `update_task`

Edit an existing task. **Pass only the fields you want to change** — anything
omitted keeps its current value. This means you can reschedule or (un)star a
task without re-sending its title.

- **Parameters:**
  - `uri` (string, required) — from `list_tasks`
  - `title` (string, optional) — new title; empty = keep existing title
  - `date` (string, optional) — new due date `YYYY-MM-DD`; empty = keep existing date
  - `starred` (bool, optional) — `true` = add star, `false` = remove star, omit = keep unchanged
- **Returns:** confirmation string

### `complete_task`

Mark a task as done. This **removes it from the server**, same as checking it
off in the app.

- **Parameters:**
  - `uri` (string, required) — from `list_tasks`
- **Returns:** confirmation string

### `catchup`

Move every overdue task to today's date. Same as "Catch Up" in the desktop app.

- **Parameters:** none
- **Returns:** summary string with the number of tasks moved

### `list_calendars` *(setup)*

List all calendars available on the CalDAV server.

- **Parameters:** none
- **Returns:** a list of `{ "name": ..., "url": ... }` objects

### `set_calendar` *(setup)*

Switch the active calendar and persist the choice to the config.

- **Parameters:**
  - `calendar_url` (string, required) — a URL from `list_calendars`
- **Returns:** confirmation string with the calendar name

## Typical flows

The client picks the tools automatically — these are the kinds of prompts that
map onto them:

- *"What's on my list?"* → `list_tasks`
- *"Add a starred task to call the dentist tomorrow"* → `create_task`, then
  `update_task` with `starred: true`
- *"Push the tax return to next Friday"* → `list_tasks` → `update_task` (date only)
- *"I finished the grocery shopping"* → `list_tasks` → `complete_task`
- *"Catch me up — move everything overdue to today"* → `catchup`
- *"Switch to my Work calendar"* → `list_calendars` → `set_calendar`
