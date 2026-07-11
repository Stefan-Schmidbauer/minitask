import logging
import uuid
from datetime import date, datetime, timezone

import caldav

from src.models.task import Task

logger = logging.getLogger("minitask.caldav")


class CalDAVService:
    def __init__(self):
        self._client: caldav.DAVClient | None = None
        self._principal: caldav.Principal | None = None
        self._calendar: caldav.Calendar | None = None

    def connect(self, url: str, username: str, password: str) -> bool:
        try:
            self._client = caldav.DAVClient(url=url, username=username, password=password)
            self._principal = self._client.principal()
            logger.info("Connected to CalDAV server: %s", url)
            return True
        except Exception as e:
            logger.error("Connection failed: %s", e)
            raise ConnectionError(str(e)) from e

    def get_calendars(self) -> list[dict]:
        if not self._principal:
            return []
        calendars = []
        for cal in self._principal.calendars():
            name = cal.name or str(cal.url)
            calendars.append({
                "url": str(cal.url),
                "name": name,
            })
        return calendars

    def set_current_calendar(self, calendar_url: str) -> None:
        if not self._client:
            raise ConnectionError("Not connected")
        self._calendar = caldav.Calendar(client=self._client, url=calendar_url)
        logger.info("Calendar set: %s", calendar_url)

    def get_tasks(self) -> list[Task]:
        if not self._calendar:
            raise ConnectionError("No calendar selected")
        tasks = []
        try:
            todos = self._calendar.todos(include_completed=False)
        except Exception as e:
            logger.error("Failed to fetch tasks: %s", e)
            raise
        for todo_obj in todos:
            try:
                task = self._parse_todo(todo_obj)
                if task:
                    tasks.append(task)
            except Exception as e:
                logger.warning("Failed to parse todo: %s", e)
        return tasks

    def create_task(self, title: str, date_str: str = "", note: str = "") -> bool:
        if not self._calendar:
            raise ConnectionError("No calendar selected")
        uid = str(uuid.uuid4()).upper()
        now = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MiniTask//EN",
            "BEGIN:VTODO",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"CREATED:{now}",
            f"SUMMARY:{self._escape_ical(title)}",
            "STATUS:NEEDS-ACTION",
        ]
        if date_str:
            lines.append(f"DUE;VALUE=DATE:{date_str.replace('-', '')}")
        if note:
            lines.append(f"DESCRIPTION:{self._escape_ical(note)}")
        lines += ["END:VTODO", "END:VCALENDAR"]
        try:
            self._calendar.save_todo("\r\n".join(lines) + "\r\n")
            logger.info("Task created: %s", title)
            return True
        except Exception as e:
            logger.error("Failed to create task: %s", e)
            raise

    def update_task(self, uri: str, title: str = "", date_str: str = "",
                    starred: bool | None = None, note: str | None = None) -> bool:
        if not self._calendar:
            raise ConnectionError("No calendar selected")
        try:
            todo_obj = caldav.Todo(client=self._client, url=uri, parent=self._calendar)
            todo_obj.load()

            uid = ""
            existing_summary = ""
            existing_due = ""
            existing_priority = ""
            for line in todo_obj.data.splitlines():
                if line.startswith("UID:"):
                    uid = line[4:].strip()
                elif line.startswith("SUMMARY"):
                    existing_summary = line
                elif line.upper().startswith("DUE"):
                    existing_due = line
                elif line.startswith("PRIORITY:"):
                    existing_priority = line

            # DESCRIPTION can be folded across multiple physical lines, so read it
            # via the icalendar parser (which unfolds/unescapes) instead of raw lines.
            existing_note = ""
            try:
                for component in todo_obj.icalendar_instance.walk("VTODO"):
                    desc = component.get("description")
                    if desc:
                        existing_note = str(desc)
                    break
            except Exception as e:
                logger.warning("Failed to read existing description: %s", e)

            now = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//MiniTask//EN",
                "BEGIN:VTODO",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
            ]

            if title:
                lines.append(f"SUMMARY:{self._escape_ical(title)}")
            elif existing_summary:
                lines.append(existing_summary)

            if date_str:
                lines.append(f"DUE;VALUE=DATE:{date_str.replace('-', '')}")
            elif existing_due:
                lines.append(existing_due)

            if starred is True:
                lines.append("PRIORITY:1")
            elif starred is None and existing_priority:
                lines.append(existing_priority)
            # starred is False → kein PRIORITY-Eintrag = Stern entfernen

            # note is None → keep existing; "" → clear; text → set
            if note is not None:
                if note:
                    lines.append(f"DESCRIPTION:{self._escape_ical(note)}")
            elif existing_note:
                lines.append(f"DESCRIPTION:{self._escape_ical(existing_note)}")

            lines.append("STATUS:NEEDS-ACTION")

            lines += ["END:VTODO", "END:VCALENDAR"]

            todo_obj.data = "\r\n".join(lines) + "\r\n"
            todo_obj.save()
            logger.info("Task updated: %s", uri)
            return True
        except Exception as e:
            logger.error("Failed to update task: %s", e)
            raise

    @staticmethod
    def _escape_ical(text: str) -> str:
        if not text:
            return ""
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    def delete_task(self, uri: str) -> bool:
        if not self._calendar:
            raise ConnectionError("No calendar selected")
        try:
            self._client.delete(uri)
            logger.info("Task deleted: %s", uri)
            return True
        except Exception as e:
            logger.error("Failed to delete task: %s", e)
            raise

    def _parse_todo(self, todo_obj) -> Task | None:
        try:
            ical = todo_obj.icalendar_instance
            for component in ical.walk("VTODO"):
                uid = str(component.get("uid", ""))
                summary = str(component.get("summary", "Untitled"))
                due = component.get("due")
                date_str = ""
                if due:
                    due_val = due.dt
                    if isinstance(due_val, datetime):
                        date_str = due_val.strftime("%Y-%m-%d")
                    elif isinstance(due_val, date):
                        date_str = due_val.isoformat()
                priority = component.get("priority")
                starred = int(str(priority)) == 1 if priority else False
                completed = component.get("completed") is not None
                description = component.get("description")
                note = str(description) if description else ""
                return Task(
                    id=uid,
                    uri=str(todo_obj.url),
                    title=summary,
                    date=date_str,
                    completed=completed,
                    starred=starred,
                    note=note,
                )
        except Exception as e:
            logger.warning("Parse error: %s", e)
        return None
