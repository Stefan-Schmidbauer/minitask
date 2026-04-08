import logging
from datetime import date, datetime

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.models.task import Task
from src.services.caldav_client import CalDAVService
from src.services.config_manager import ConfigManager
from src.utils.date_helpers import increment_date, increment_month, today_iso
from src.utils.sorting import sort_tasks
from src.views.edit_dialog import EditDialog
from src.views.settings_dialog import SettingsDialog
from src.views.task_widgets import TaskTable

logger = logging.getLogger("minitask.ui")

AUTO_SYNC_INTERVAL = 60000  # 60 seconds
UNDO_TIMEOUT = 5000  # 5 seconds to undo


class CalDAVWorker(QThread):
    tasks_loaded = Signal(list)
    operation_done = Signal()
    error = Signal(str)

    def __init__(self, service: CalDAVService, operation: str, **kwargs):
        super().__init__()
        self.service = service
        self.operation = operation
        self.kwargs = kwargs
        self._is_auto_sync = kwargs.pop("_auto_sync", False)

    @property
    def is_auto_sync(self):
        return self._is_auto_sync

    def run(self):
        try:
            if self.operation == "load":
                tasks = self.service.get_tasks()
                self.tasks_loaded.emit(tasks)
            elif self.operation == "create":
                self.service.create_task(self.kwargs["title"], self.kwargs.get("date", ""))
                self.operation_done.emit()
            elif self.operation == "update":
                self.service.update_task(**self.kwargs)
                self.operation_done.emit()
            elif self.operation == "catch_up":
                for task in self.kwargs["tasks"]:
                    self.service.update_task(
                        uri=task.uri,
                        title=task.title,
                        date_str=self.kwargs["today"],
                        starred=task.starred,
                    )
                self.operation_done.emit()
            elif self.operation == "delete":
                self.service.delete_task(self.kwargs["uri"])
                self.operation_done.emit()
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, service: CalDAVService, config_manager: ConfigManager):
        super().__init__()
        self.service = service
        self.config_manager = config_manager
        self.tasks: list[Task] = []
        self._worker: CalDAVWorker | None = None
        self._search_text = ""
        self._pending_delete: dict | None = None  # For undo
        self._undo_timer: QTimer | None = None
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_auto_sync()
        self._restore_geometry()
        self._load_tasks()

    def _setup_ui(self):
        self.setWindowTitle("MiniTask")
        self.setMinimumSize(700, 500)

        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        settings_action = QAction("\u2699 Settings", self)
        settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(settings_action)

        toolbar.addSeparator()

        refresh_action = QAction("\u21bb Refresh", self)
        refresh_action.triggered.connect(self._load_tasks)
        toolbar.addAction(refresh_action)

        catch_up_action = QAction("\u23ed Catch Up", self)
        catch_up_action.setToolTip("Set all overdue tasks to today")
        catch_up_action.triggered.connect(self._catch_up)
        toolbar.addAction(catch_up_action)

        toolbar.addSeparator()

        self._auto_sync_checkbox = QCheckBox("Auto-Sync")
        self._auto_sync_checkbox.setToolTip("Sync every 60 seconds")
        self._auto_sync_checkbox.setChecked(True)
        self._auto_sync_checkbox.toggled.connect(self._on_auto_sync_toggled)
        toolbar.addWidget(self._auto_sync_checkbox)

        toolbar.addSeparator()

        self._on_top_checkbox = QCheckBox("On Top")
        self._on_top_checkbox.setToolTip("Keep window always on top")
        self._on_top_checkbox.toggled.connect(self._on_always_on_top_toggled)
        toolbar.addWidget(self._on_top_checkbox)

        # About and Quit removed from toolbar — they live in the bottom bar now

        # --- Central Widget ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Add task bar
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("New task... (Ctrl+N)")
        self.title_input.setStyleSheet(
            "padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px;"
        )
        self.title_input.returnPressed.connect(self._add_task)
        add_layout.addWidget(self.title_input, stretch=1)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(date.today())
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        self.date_input.setMinimumWidth(150)
        self.date_input.setStyleSheet(
            "QDateEdit { padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }"
            "QDateEdit::drop-down { width: 28px; }"
        )
        calendar = self.date_input.calendarWidget()
        calendar.setStyleSheet(
            "QCalendarWidget QToolButton {"
            "  color: #333; font-size: 13px; font-weight: bold;"
            "  background: #f0f0f0; padding: 4px 8px;"
            "}"
            "QCalendarWidget QToolButton:hover {"
            "  background: #e0e0e0;"
            "}"
            "QCalendarWidget QWidget#qt_calendar_navigationbar {"
            "  background: #f0f0f0;"
            "}"
            "QCalendarWidget QSpinBox {"
            "  color: #333; font-size: 13px; font-weight: bold;"
            "  background: #f0f0f0; selection-background-color: #337ab7;"
            "}"
        )
        add_layout.addWidget(self.date_input)

        self.add_btn = QPushButton("Add")
        self.add_btn.setStyleSheet(
            "QPushButton { background: #337ab7; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: #286090; }"
            "QPushButton:disabled { background: #aaa; }"
        )
        self.add_btn.clicked.connect(self._add_task)
        add_layout.addWidget(self.add_btn)

        main_layout.addLayout(add_layout)

        # Search + task count row
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\U0001f50d Search tasks... (Ctrl+F)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(
            "padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px;"
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_input, stretch=1)

        main_layout.addLayout(filter_layout)

        # Undo bar (hidden by default)
        self.undo_bar = QWidget()
        self.undo_bar.setStyleSheet(
            "background: #fcf8e3; border: 1px solid #faebcc; border-radius: 4px; padding: 4px;"
        )
        undo_layout = QHBoxLayout(self.undo_bar)
        undo_layout.setContentsMargins(8, 4, 8, 4)
        self.undo_label = QLabel("")
        self.undo_label.setStyleSheet("color: #8a6d3b; font-size: 12px;")
        undo_layout.addWidget(self.undo_label, stretch=1)
        undo_btn = QPushButton("Undo")
        undo_btn.setStyleSheet(
            "QPushButton { background: #f0ad4e; color: white; padding: 4px 12px; "
            "border: none; border-radius: 3px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #ec971f; }"
        )
        undo_btn.clicked.connect(self._undo_complete)
        undo_layout.addWidget(undo_btn)
        self.undo_bar.hide()
        main_layout.addWidget(self.undo_bar)

        # Task table
        self.task_table = TaskTable()
        self.task_table.star_toggled.connect(self._on_star_toggle)
        self.task_table.complete_toggled.connect(self._on_complete)
        self.task_table.edit_requested.connect(self._on_edit)
        self.task_table.increment_requested.connect(self._on_increment)
        self.task_table.increment_week_requested.connect(self._on_increment_week)
        self.task_table.increment_month_requested.connect(self._on_increment_month)
        self.task_table.today_requested.connect(self._on_set_today)
        main_layout.addWidget(self.task_table, stretch=1)

        # Bottom bar: status label + buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        bottom_layout.addWidget(self.status_label, stretch=1)

        blue_btn_style = (
            "QPushButton { background: #337ab7; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: #286090; }"
        )

        about_btn = QPushButton("About")
        about_btn.setStyleSheet(blue_btn_style)
        about_btn.clicked.connect(self._show_about)
        bottom_layout.addWidget(about_btn)

        quit_btn = QPushButton("Quit")
        quit_btn.setStyleSheet(blue_btn_style)
        quit_btn.clicked.connect(self.close)
        bottom_layout.addWidget(quit_btn)

        main_layout.addLayout(bottom_layout)

    # --- Keyboard Shortcuts ---

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self, self._focus_new_task)
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)
        QShortcut(QKeySequence("F5"), self, self._load_tasks)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_complete)

    def _focus_new_task(self):
        self.title_input.setFocus()
        self.title_input.selectAll()

    def _focus_search(self):
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _clear_search(self):
        if self.search_input.hasFocus() and self.search_input.text():
            self.search_input.clear()
        else:
            self.search_input.clear()
            self.title_input.setFocus()

    # --- About ---

    def _get_version(self) -> str:
        import pathlib
        import subprocess

        repo_dir = pathlib.Path(__file__).resolve().parent.parent.parent
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "dev"

    def _show_about(self):
        import pathlib

        icon_path = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "minitask.svg"
        pixmap = QPixmap(str(icon_path)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        version = self._get_version()

        msg = QMessageBox(self)
        msg.setWindowTitle("About MiniTask")
        msg.setIconPixmap(pixmap)
        msg.setText(
            f"<h3>MiniTask</h3>"
            f"<p>Version: {version}</p>"
            f"<p>A lightweight CalDAV task manager.</p>"
        )
        msg.setInformativeText(
            "<p>Built with PySide6 (Qt6) and python-caldav.</p>"
            "<p>&copy; 2025 Stefan Schmidbauer &amp; Claude (Anthropic)</p>"
            "<p><b>Shortcuts:</b> Ctrl+N new task, Ctrl+F search, "
            "F5 refresh, Ctrl+Z undo, Escape clear</p>"
        )
        msg.exec()

    # --- Auto-Sync ---

    def _setup_auto_sync(self):
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._auto_sync)
        self._sync_timer.start(AUTO_SYNC_INTERVAL)

    def _auto_sync(self):
        """Auto-sync: load tasks silently (no error dialog on failure)."""
        if self._worker and self._worker.isRunning():
            return
        self._worker = CalDAVWorker(self.service, "load", _auto_sync=True)
        self._worker.tasks_loaded.connect(self._on_tasks_loaded)
        self._worker.error.connect(self._on_auto_sync_error)
        self._worker.start()

    def _on_auto_sync_error(self, msg: str):
        self.status_label.setText(f"Sync error: {msg}")

    def _on_auto_sync_toggled(self, checked: bool):
        if checked:
            self._sync_timer.start(AUTO_SYNC_INTERVAL)
            self.status_label.setText("Auto-sync enabled")
        else:
            self._sync_timer.stop()
            self.status_label.setText("Auto-sync disabled")

    # --- Always on Top ---

    def _on_always_on_top_toggled(self, checked: bool):
        geo = self.geometry()
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(geo)
        self.show()

    # --- Search ---

    def _on_search_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._render_tasks()

    def _get_filtered_tasks(self) -> list[Task]:
        if not self._search_text:
            return self.tasks
        return [t for t in self.tasks if self._search_text in t.title.lower()]

    # --- Window Geometry ---

    def _restore_geometry(self):
        config = self.config_manager.load()
        geo = config.get("window_geometry")
        if geo:
            self.setGeometry(geo["x"], geo["y"], geo["w"], geo["h"])

    def _save_geometry(self):
        geo = self.geometry()
        config = self.config_manager.load()
        config["window_geometry"] = {
            "x": geo.x(), "y": geo.y(), "w": geo.width(), "h": geo.height()
        }
        self.config_manager.save(config)

    def closeEvent(self, event):
        self._save_geometry()
        # If there's a pending delete, execute it before closing
        if self._pending_delete:
            self._execute_pending_delete()
        super().closeEvent(event)

    # --- Undo ---

    def _on_complete(self, uri: str):
        task = self._find_task(uri)
        if not task:
            return

        # Cancel any previous pending delete
        if self._pending_delete:
            self._execute_pending_delete()

        # Store for undo instead of deleting immediately
        self._pending_delete = {"uri": uri, "task": task}

        # Remove from local list and re-render
        self.tasks = [t for t in self.tasks if t.uri != uri]
        self._render_tasks()

        # Show undo bar
        self.undo_label.setText(f'Completed "{task.title}" — deleting in 5s...')
        self.undo_bar.show()

        # Start undo timer
        if self._undo_timer:
            self._undo_timer.stop()
        self._undo_timer = QTimer(self)
        self._undo_timer.setSingleShot(True)
        self._undo_timer.timeout.connect(self._execute_pending_delete)
        self._undo_timer.start(UNDO_TIMEOUT)

    def _undo_complete(self):
        if not self._pending_delete:
            return
        # Restore task to local list
        task = self._pending_delete["task"]
        self._pending_delete = None
        if self._undo_timer:
            self._undo_timer.stop()
        self.undo_bar.hide()
        self.tasks.append(task)
        self.tasks = sort_tasks(self.tasks)
        self._render_tasks()
        self.status_label.setText(f'Undo: "{task.title}" restored')

    def _execute_pending_delete(self):
        if not self._pending_delete:
            return
        uri = self._pending_delete["uri"]
        self._pending_delete = None
        if self._undo_timer:
            self._undo_timer.stop()
        self.undo_bar.hide()
        self._run_worker("delete", uri=uri)

    # --- Worker ---

    def _run_worker(self, operation: str, **kwargs):
        if self._worker and self._worker.isRunning():
            return
        self._set_busy(True)
        self._worker = CalDAVWorker(self.service, operation, **kwargs)
        self._worker.tasks_loaded.connect(self._on_tasks_loaded)
        self._worker.operation_done.connect(self._load_tasks)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _set_busy(self, busy: bool):
        self.add_btn.setEnabled(not busy)
        if busy:
            self.status_label.setText("Loading...")

    def _load_tasks(self):
        today = date.today()
        if self.date_input.date().toPython() < today:
            self.date_input.setDate(today)
        self._run_worker("load")

    def _on_tasks_loaded(self, tasks: list[Task]):
        self._set_busy(False)
        self.tasks = sort_tasks(tasks)
        self._render_tasks()
        now = datetime.now().strftime("%H:%M:%S")
        self.status_label.setText(f"{len(self.tasks)} tasks loaded ({now})")

    def _on_error(self, msg: str):
        self._set_busy(False)
        self.status_label.setText(f"Error: {msg}")
        QMessageBox.warning(self, "Error", msg)

    def _render_tasks(self):
        filtered = self._get_filtered_tasks()
        self.task_table.set_tasks(filtered)
        if self._search_text:
            self.status_label.setText(f"Search: {len(filtered)}/{len(self.tasks)} tasks")

    def _add_task(self):
        title = self.title_input.text().strip()
        if not title:
            return
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        self.title_input.clear()
        self._run_worker("create", title=title, date=date_str)

    def _find_task(self, uri: str) -> Task | None:
        for t in self.tasks:
            if t.uri == uri:
                return t
        return None

    def _on_star_toggle(self, uri: str, starred: bool):
        task = self._find_task(uri)
        if not task:
            return
        self._run_worker(
            "update", uri=uri, title=task.title, date_str=task.date, starred=starred
        )

    def _on_edit(self, uri: str):
        task = self._find_task(uri)
        if not task:
            return

        dialog = EditDialog(task.title, task.date, self)
        if dialog.exec() == EditDialog.DialogCode.Accepted:
            result = dialog.get_result()
            if result:
                new_title, new_date = result
                self._run_worker(
                    "update",
                    uri=uri,
                    title=new_title,
                    date_str=new_date,
                    starred=task.starred,
                )

    def _on_increment(self, uri: str):
        task = self._find_task(uri)
        if not task:
            return
        new_date = increment_date(task.date)
        self._run_worker(
            "update", uri=uri, title=task.title, date_str=new_date, starred=task.starred
        )

    def _on_increment_week(self, uri: str):
        task = self._find_task(uri)
        if not task:
            return
        new_date = increment_date(task.date, days=7)
        self._run_worker(
            "update", uri=uri, title=task.title, date_str=new_date, starred=task.starred
        )

    def _on_increment_month(self, uri: str):
        task = self._find_task(uri)
        if not task:
            return
        new_date = increment_month(task.date)
        self._run_worker(
            "update", uri=uri, title=task.title, date_str=new_date, starred=task.starred
        )

    def _on_set_today(self, uri: str):
        task = self._find_task(uri)
        if not task:
            return
        self._run_worker(
            "update",
            uri=uri,
            title=task.title,
            date_str=today_iso(),
            starred=task.starred,
        )

    def _catch_up(self):
        today = today_iso()
        overdue = [t for t in self.tasks if t.date and t.date < today]
        if not overdue:
            self.status_label.setText("No overdue tasks")
            return
        reply = QMessageBox.question(
            self,
            "Catch Up",
            f"Set {len(overdue)} overdue task(s) to today?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_worker("catch_up", tasks=overdue, today=today)

    def _open_settings(self):
        config = self.config_manager.load()
        dialog = SettingsDialog(config, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            if new_config:
                self.config_manager.save(new_config)
                try:
                    self.service.connect(
                        new_config["server_url"],
                        new_config["username"],
                        new_config["password"],
                    )
                    self.service.set_current_calendar(new_config["calendar_url"])
                    self._load_tasks()
                except Exception as e:
                    QMessageBox.critical(self, "Connection Error", str(e))
