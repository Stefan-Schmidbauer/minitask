import logging
from datetime import date, datetime, timezone

import caldav
from icalendar import Calendar, Todo

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

    def create_task(self, title: str, date_str: str = "") -> bool:
        if not self._calendar:
            raise ConnectionError("No calendar selected")
        cal = Calendar()
        cal.add("prodid", "-//MiniTask//EN")
        cal.add("version", "2.0")
        todo = Todo()
        todo.add("summary", title)
        todo.add("status", "NEEDS-ACTION")
        todo.add("created", datetime.now(tz=timezone.utc))
        todo.add("dtstamp", datetime.now(tz=timezone.utc))
        if date_str:
            try:
                year, month, day = date_str.split("-")
                todo.add("due", date(int(year), int(month), int(day)))
            except (ValueError, TypeError):
                pass
        cal.add_component(todo)
        try:
            self._calendar.save_todo(cal.to_ical().decode("utf-8"))
            logger.info("Task created: %s", title)
            return True
        except Exception as e:
            logger.error("Failed to create task: %s", e)
            raise

    def update_task(self, uri: str, title: str, date_str: str,
                    completed: bool = False, starred: bool | None = None) -> bool:
        if not self._calendar:
            raise ConnectionError("No calendar selected")
        try:
            # Fetch the existing todo from the server
            todo_obj = caldav.Todo(client=self._client, url=uri, parent=self._calendar)
            todo_obj.load()

            # Extract UID from existing data
            uid = ""
            for line in todo_obj.data.splitlines():
                if line.startswith("UID:"):
                    uid = line[4:].strip()
                    break

            # Build new iCalendar string from scratch (same approach as mini-task-gui)
            now = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            lines = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//MiniTask//EN",
                "BEGIN:VTODO",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"SUMMARY:{self._escape_ical(title)}",
            ]

            if date_str:
                due = date_str.replace("-", "")
                lines.append(f"DUE;VALUE=DATE:{due}")

            if starred is not None and starred:
                lines.append("PRIORITY:1")

            if completed:
                lines.append("STATUS:COMPLETED")
                lines.append(f"COMPLETED:{now}")
                lines.append("PERCENT-COMPLETE:100")
            else:
                lines.append("STATUS:NEEDS-ACTION")

            lines.append("END:VTODO")
            lines.append("END:VCALENDAR")

            new_data = "\r\n".join(lines) + "\r\n"

            # Set data and save (same pattern as mini-task-gui: server_task.data = ...; server_task.save())
            todo_obj.data = new_data
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
                return Task(
                    id=uid,
                    uri=str(todo_obj.url),
                    title=summary,
                    date=date_str,
                    completed=completed,
                    starred=starred,
                )
        except Exception as e:
            logger.warning("Parse error: %s", e)
        return None
