from dataclasses import dataclass


@dataclass
class Task:
    id: str
    uri: str
    title: str
    date: str = ""
    completed: bool = False
    starred: bool = False
