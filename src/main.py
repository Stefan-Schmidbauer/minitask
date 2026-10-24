import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from src.services.caldav_client import CalDAVService
from src.services.config_manager import ConfigManager
from src.utils.single_instance import SingleInstance
from src.views.main_window import MainWindow
from src.views.settings_dialog import SettingsDialog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MiniTask")
    app.setStyle("Fusion")

    single_instance = SingleInstance(app)
    if single_instance.notify_running_instance():
        sys.exit(0)
    single_instance.listen()

    try:
        config_manager = ConfigManager()
    except RuntimeError as e:
        QMessageBox.critical(None, "Keyring Error", str(e))
        sys.exit(1)
    service = CalDAVService()

    config = config_manager.load() if config_manager.exists() else {}

    if not config or not config.get("server_url") or not config.get("password"):
        dialog = SettingsDialog(config)
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            sys.exit(0)
        config = dialog.get_config()
        if config:
            config_manager.save(config)

    if config:
        try:
            service.connect(config["server_url"], config["username"], config["password"])
            service.set_current_calendar(config["calendar_url"])
        except Exception as e:
            QMessageBox.critical(None, "Connection Error", str(e))
            dialog = SettingsDialog(config)
            if dialog.exec() != SettingsDialog.DialogCode.Accepted:
                sys.exit(1)
            config = dialog.get_config()
            if config:
                config_manager.save(config)
                service.connect(
                    config["server_url"], config["username"], config["password"]
                )
                service.set_current_calendar(config["calendar_url"])

    window = MainWindow(service, config_manager)
    single_instance.activation_requested.connect(window.bring_to_front)
    window.show()
    sys.exit(app.exec())
