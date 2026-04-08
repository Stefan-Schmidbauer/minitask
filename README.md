# MiniTask

A lightweight CalDAV task manager desktop application built with PySide6 (Qt6) and python-caldav.

![MiniTask Screenshot](assets/screenshot.png)

## Features

- Connect to any CalDAV server (e.g. Nextcloud, mailbox.org, Radicale)
- Create, edit, and complete tasks with due dates
- Calendar popup for date selection
- Postpone tasks by +1 day, +1 week, or +1 month
- Set any task to today with one click
- "Catch Up" — set all overdue tasks to today at once
- Star/prioritize important tasks
- Color-coded due dates (overdue, today, future)
- Search and filter tasks
- Auto-sync every 60 seconds (toggleable)
- Undo completed (deleted) tasks within 5 seconds
- Keyboard shortcuts for fast workflow
- Always-on-top mode
- Secure credential storage via system keyring
- Remembers window position between sessions

## Requirements

- Python 3.12+
- Linux (Debian/Ubuntu-based)
- A CalDAV server with task/todo support

## Installation

MiniTask uses [Quickstrap](README.quickstrap.md) for installation and startup.

```bash
./install.py
```

This interactively sets up a virtual environment, installs system dependencies (`libgl1`, `libegl1`) and Python packages (`PySide6`, `caldav`, `icalendar`).

## Usage

```bash
./start.sh
```

On first launch, you will be prompted to enter your CalDAV server credentials and select a calendar.

### Developer Mode

```bash
source quickstrap/activate.sh
python main.py
```

## Keyboard Shortcuts

| Shortcut   | Action              |
|------------|---------------------|
| `Ctrl+N`   | Focus new task input |
| `Ctrl+F`   | Focus search         |
| `F5`       | Refresh tasks        |
| `Ctrl+Z`   | Undo last completion |
| `Escape`   | Clear search         |

## Configuration

Settings are stored in:

- **Linux:** `~/.config/minitask/settings.json`
- **Windows:** `%APPDATA%/minitask/settings.json`

### Credential Storage

Passwords are stored securely in the system keyring (GNOME Keyring, KWallet, or Windows Credential Locker) and never written to the config file. The keyring access runs in an isolated subprocess to avoid conflicts with Qt.

A running keyring service is required (e.g. `gnome-keyring`, `kwallet`).

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Authors

- Stefan Schmidbauer
- Claude (AI Assistant by Anthropic)
