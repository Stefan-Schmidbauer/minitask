import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("minitask.config")

KEYRING_SERVICE = "minitask"


def _keyring_available() -> bool:
    if os.name == "nt":
        # On Windows: call keyring directly — no Qt/D-Bus conflicts exist
        try:
            import keyring
            keyring.get_password(KEYRING_SERVICE, "__probe__")
            return True
        except Exception:
            return False
    else:
        # On Linux/Mac: use subprocess to avoid SecretService/D-Bus segfaults in Qt
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 "import keyring; keyring.get_password('minitask', '__probe__')"],
                capture_output=True, timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False


def _keyring_get(username: str) -> str | None:
    if os.name == "nt":
        try:
            import keyring
            return keyring.get_password(KEYRING_SERVICE, username)
        except Exception as e:
            logger.warning("Failed to load password from keyring: %s", e)
            return None
    else:
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 "import sys, keyring; p = keyring.get_password(sys.argv[1], sys.argv[2]);"
                 "print(p or '', end='')",
                 KEYRING_SERVICE, username],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except Exception as e:
            logger.warning("Failed to load password from keyring: %s", e)
        return None


def _keyring_set(username: str, password: str) -> bool:
    if os.name == "nt":
        try:
            import keyring
            keyring.set_password(KEYRING_SERVICE, username, password)
            return True
        except Exception as e:
            logger.warning("Failed to save password to keyring: %s", e)
            return False
    else:
        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 "import sys, keyring;"
                 "keyring.set_password(sys.argv[1], sys.argv[2], sys.stdin.read())",
                 KEYRING_SERVICE, username],
                input=password, capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning("Failed to save password to keyring: %s", e)
        return False


class ConfigManager:
    def __init__(self, config_dir: Path | None = None):
        self._config_dir = config_dir or self._get_default_config_dir()
        self._config_file = self._config_dir / "settings.json"
        if not _keyring_available():
            if os.name == "nt":
                raise RuntimeError(
                    "System keyring not available. "
                    "Please ensure the Windows Credential Manager service is running."
                )
            raise RuntimeError(
                "System keyring not available. "
                "Please ensure a keyring service is running (e.g. gnome-keyring, kwallet)."
            )

    def _get_default_config_dir(self) -> Path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "minitask"

    def exists(self) -> bool:
        return self._config_file.exists()

    def load(self) -> dict:
        if not self._config_file.exists():
            return {}
        with open(self._config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        username = config.get("username", "")
        if username and not config.get("password"):
            password = _keyring_get(username)
            if password:
                config["password"] = password
        config.setdefault("password", "")
        return config

    def save(self, settings: dict) -> None:
        username = settings.get("username", "")
        password = settings.get("password", "")
        if username and password:
            _keyring_set(username, password)
        json_settings = {k: v for k, v in settings.items() if k != "password"}
        self._save_json(json_settings)

    def _save_json(self, settings: dict) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

    def get_config_path(self) -> Path:
        return self._config_file
