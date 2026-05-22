#!/usr/bin/env python3
"""MiniTask MCP Server — exposes CalDAV task management as Claude tools."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from src.services.caldav_client import CalDAVService
from src.services.config_manager import ConfigManager

mcp = FastMCP("minitask")

_PROJECT_DIR = Path(__file__).parent
_service = CalDAVService()
_connected = False


def _get_config_manager() -> ConfigManager:
    local_manager = ConfigManager(config_dir=_PROJECT_DIR)
    if local_manager.exists():
        return local_manager
    return ConfigManager()


def _load_config() -> dict:
    return _get_config_manager().load()


def _ensure_connected() -> None:
    global _connected
    if _connected:
        return

    config = _load_config()

    url = config.get("server_url", "")
    username = config.get("username", "")
    password = config.get("password", "")
    calendar_url = config.get("calendar_url", "")

    if not all([url, username, password]):
        raise RuntimeError(
            "MiniTask is not configured yet. "
            "Run setup_credentials.py to set up your CalDAV credentials."
        )

    _service.connect(url, username, password)

    if calendar_url:
        _service.set_current_calendar(calendar_url)

    _connected = True


@mcp.tool()
def list_calendars() -> list[dict]:
    """List all available calendars on the CalDAV server."""
    _ensure_connected()
    return _service.get_calendars()


@mcp.tool()
def set_calendar(calendar_url: str) -> str:
    """Switch to a different calendar by URL. Use list_calendars to find the URL."""
    _ensure_connected()
    _service.set_current_calendar(calendar_url)
    manager = _get_config_manager()
    config = manager.load()
    config["calendar_url"] = calendar_url
    calendars = _service.get_calendars()
    match = next((c for c in calendars if c["url"] == calendar_url), None)
    if match:
        config["calendar_name"] = match["name"]
    manager.save(config)
    return f"Calendar set: {match['name'] if match else calendar_url}"


@mcp.tool()
def list_tasks() -> list[dict]:
    """List all open (incomplete) tasks in the current calendar."""
    _ensure_connected()
    tasks = _service.get_tasks()
    return [
        {
            "id": t.id,
            "uri": t.uri,
            "title": t.title,
            "date": t.date,
            "starred": t.starred,
            "completed": t.completed,
        }
        for t in tasks
    ]


@mcp.tool()
def create_task(title: str, date: str = "") -> str:
    """Create a new task. Date format: YYYY-MM-DD (e.g. 2026-05-30). Defaults to today if omitted."""
    _ensure_connected()
    if not date:
        from datetime import date as _date
        date = _date.today().isoformat()
    _service.create_task(title, date)
    return f"Task created: {title}"


@mcp.tool()
def update_task(
    uri: str,
    title: str,
    date: str = "",
    starred: bool | None = None,
) -> str:
    """Update an existing task. The URI comes from list_tasks.

    Args:
        uri: Task URI (from list_tasks)
        title: Task title — always required; pass the current title from list_tasks if not changing it
        date: Due date (YYYY-MM-DD), empty = keep existing date
        starred: True = add star, False = remove star, omit = keep unchanged
    """
    _ensure_connected()
    _service.update_task(uri, title, date, False, starred)
    return f"Task updated: {title}"


@mcp.tool()
def complete_task(uri: str) -> str:
    """Mark a task as done — removes it from the server, same as checking it off in the app.

    Args:
        uri: Task URI (from list_tasks)
    """
    _ensure_connected()
    _service.delete_task(uri)
    return "Task completed."



@mcp.tool()
def catchup() -> str:
    """Set all overdue tasks to today. Same as 'Catch Up' in the desktop app."""
    _ensure_connected()
    from datetime import date
    today = date.today().isoformat()
    tasks = _service.get_tasks()
    overdue = [t for t in tasks if t.date and t.date < today]
    for task in overdue:
        _service.update_task(task.uri, task.title, today, False, task.starred)
    return f"{len(overdue)} overdue task(s) moved to today ({today})."


if __name__ == "__main__":
    mcp.run()
