from src.models.task import Task


def sort_tasks(tasks: list[Task]) -> list[Task]:
    """Sort tasks: starred always on top, then by date ascending, then alphabetical by title."""
    def sort_key(task: Task):
        starred_val = 0 if task.starred else 1
        has_date = 0 if not task.date else 1
        date_val = task.date if task.date else ""
        return (starred_val, has_date, date_val, task.title.lower())

    return sorted(tasks, key=sort_key)
