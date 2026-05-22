#!/usr/bin/env python3
"""MiniTask Credential Setup — configure CalDAV connection without the desktop app."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.caldav_client import CalDAVService
from src.services.config_manager import ConfigManager

PROJECT_DIR = Path(__file__).parent


def prompt(label: str, secret: bool = False) -> str:
    if secret:
        import getpass
        return getpass.getpass(f"{label}: ").strip()
    value = input(f"{label}: ").strip()
    if not value:
        print("Cannot be empty.")
        return prompt(label, secret)
    return value


def main():
    print("=" * 50)
    print("  MiniTask — CalDAV Setup")
    print("=" * 50)
    print()

    try:
        config_manager = ConfigManager(config_dir=PROJECT_DIR)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    print()

    existing = config_manager.load()
    if existing.get("server_url"):
        print("Existing configuration found:")
        print(f"  Server:   {existing['server_url']}")
        print(f"  User:     {existing['username']}")
        print(f"  Calendar: {existing.get('calendar_name', existing.get('calendar_url', '—'))}")
        print()
        overwrite = input("Reconfigure? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("Aborted.")
            return

    print("Enter your CalDAV credentials:")
    print()
    url = prompt("Server URL (e.g. https://dav.example.com/caldav)")
    username = prompt("Username")
    password = prompt("Password", secret=True)

    print()
    print("Testing connection...")

    service = CalDAVService()
    try:
        service.connect(url, username, password)
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    print("Connection successful.")
    print()

    calendars = service.get_calendars()
    if not calendars:
        print("No calendars found.")
        sys.exit(1)

    print("Available calendars:")
    for i, cal in enumerate(calendars, 1):
        print(f"  {i}) {cal['name']}")
    print()

    while True:
        try:
            choice = int(input(f"Select calendar (1-{len(calendars)}): "))
            if 1 <= choice <= len(calendars):
                break
            print(f"Please enter a number between 1 and {len(calendars)}.")
        except (ValueError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

    selected = calendars[choice - 1]
    print()
    print(f"Selected: {selected['name']}")

    config_manager.save({
        "server_url": url,
        "username": username,
        "password": password,
        "calendar_url": selected["url"],
        "calendar_name": selected["name"],
    })

    print()
    print("=" * 50)
    print("  Configuration saved!")
    print("  Password: securely stored in system keyring")
    print(f"  Config:   {config_manager.get_config_path()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
