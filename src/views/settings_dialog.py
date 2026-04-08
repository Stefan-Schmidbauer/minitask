from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.services.caldav_client import CalDAVService


class ConnectionTestWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, url, username, password):
        super().__init__()
        self.url = url
        self.username = username
        self.password = password

    def run(self):
        try:
            service = CalDAVService()
            service.connect(self.url, self.username, self.password)
            calendars = service.get_calendars()
            self.finished.emit(calendars)
        except Exception as e:
            self.error.emit(str(e))


class SettingsDialog(QDialog):
    def __init__(self, config: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MiniTask - Settings")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._result_config: dict | None = None
        self._calendars: list[dict] = []
        self._worker: ConnectionTestWorker | None = None
        self._setup_ui(config or {})

    def _setup_ui(self, config: dict):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("CalDAV Server Settings")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.url_edit = QLineEdit(config.get("server_url", "https://dav.mailbox.org"))
        self.url_edit.setPlaceholderText("https://dav.example.com/caldav/...")
        form.addRow("Server URL:", self.url_edit)

        self.user_edit = QLineEdit(config.get("username", ""))
        self.user_edit.setPlaceholderText("Username")
        form.addRow("Username:", self.user_edit)

        self.pass_edit = QLineEdit(config.get("password", ""))
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("Password")
        form.addRow("Password:", self.pass_edit)

        layout.addLayout(form)

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setStyleSheet(
            "QPushButton { background: #337ab7; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #286090; }"
            "QPushButton:disabled { background: #aaa; }"
        )
        self.test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self.test_btn)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        cal_layout = QFormLayout()
        self.cal_combo = QComboBox()
        self.cal_combo.setEnabled(False)
        cal_layout.addRow("Calendar:", self.cal_combo)
        layout.addLayout(cal_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            "QPushButton { padding: 8px 16px; border: 1px solid #ccc; "
            "border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(
            "QPushButton { background: #5cb85c; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #449d44; }"
            "QPushButton:disabled { background: #aaa; }"
        )
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _test_connection(self):
        url = self.url_edit.text().strip()
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()

        if not url or not username or not password:
            self.status_label.setText("Please fill in all fields.")
            self.status_label.setStyleSheet("color: #d9534f;")
            return

        self.test_btn.setEnabled(False)
        self.status_label.setText("Connecting...")
        self.status_label.setStyleSheet("color: #337ab7;")

        self._worker = ConnectionTestWorker(url, username, password)
        self._worker.finished.connect(self._on_connection_success)
        self._worker.error.connect(self._on_connection_error)
        self._worker.start()

    def _on_connection_success(self, calendars: list[dict]):
        self.test_btn.setEnabled(True)
        self._calendars = calendars

        self.cal_combo.clear()
        self.cal_combo.setEnabled(True)
        for cal in calendars:
            self.cal_combo.addItem(cal["name"], cal["url"])

        self.status_label.setText(f"Connected! Found {len(calendars)} calendar(s).")
        self.status_label.setStyleSheet("color: #5cb85c;")
        self.save_btn.setEnabled(len(calendars) > 0)

    def _on_connection_error(self, error_msg: str):
        self.test_btn.setEnabled(True)
        self.status_label.setText(f"Connection failed: {error_msg}")
        self.status_label.setStyleSheet("color: #d9534f;")
        self.cal_combo.clear()
        self.cal_combo.setEnabled(False)
        self.save_btn.setEnabled(False)

    def _save(self):
        idx = self.cal_combo.currentIndex()
        if idx < 0:
            return
        self._result_config = {
            "server_url": self.url_edit.text().strip(),
            "username": self.user_edit.text().strip(),
            "password": self.pass_edit.text(),
            "calendar_url": self.cal_combo.currentData(),
            "calendar_name": self.cal_combo.currentText(),
        }
        self.accept()

    def get_config(self) -> dict | None:
        return self._result_config
