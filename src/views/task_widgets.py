from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from src.utils.date_helpers import (
    COLOR_FUTURE,
    COLOR_OVERDUE,
    COLOR_STARRED,
    COLOR_TODAY,
    format_date_display,
    get_date_class,
)


COL_STAR = 0
COL_DONE = 1
COL_TITLE = 2
COL_DATE = 3
COL_ACTIONS = 4


class TaskTable(QTreeWidget):
    star_toggled = Signal(str, bool)
    complete_toggled = Signal(str)
    edit_requested = Signal(str)
    increment_requested = Signal(str)
    increment_week_requested = Signal(str)
    increment_month_requested = Signal(str)
    today_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["\u2605", "\u2713", "Title", "Due Date", "Actions"])
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIndentation(0)

        header = self.header()
        header.setMinimumSectionSize(20)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COL_STAR, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_DONE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_DATE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(COL_STAR, 24)
        self.setColumnWidth(COL_DONE, 24)
        self.setColumnWidth(COL_DATE, 110)
        self.setColumnWidth(COL_ACTIONS, 135)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.headerItem().setTextAlignment(COL_DATE, Qt.AlignmentFlag.AlignCenter)
        self.headerItem().setTextAlignment(COL_ACTIONS, Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 6px 0px;
                border-bottom: 1px solid #eee;
            }
            QTreeWidget::item:alternate {
                background: #fafafa;
            }
            QHeaderView::section {
                background: #f0f0f0;
                border: none;
                border-bottom: 2px solid #ccc;
                padding: 6px 2px;
                font-weight: bold;
                font-size: 12px;
                color: #555;
            }
        """)

        self.itemClicked.connect(self._on_click)

    def set_tasks(self, tasks):
        self.clear()
        for task in tasks:
            self._add_task_row(task)

    def _add_task_row(self, task):
        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, task.uri)
        item.setSizeHint(0, QSize(0, 42))
        self.addTopLevelItem(item)

        # Star button (wrapped for vertical centering)
        star_btn = QPushButton("\u2605" if task.starred else "\u2606")
        star_btn.setFixedSize(22, 22)
        star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if task.starred:
            star_btn.setStyleSheet(
                "border: none; background: transparent; color: #f0ad4e; font-size: 16px;"
            )
        else:
            star_btn.setStyleSheet(
                "border: none; background: transparent; color: #bbb; font-size: 16px;"
            )
        star_btn.clicked.connect(
            lambda checked, uri=task.uri, s=task.starred: self.star_toggled.emit(uri, not s)
        )
        star_widget = QWidget()
        star_layout = QHBoxLayout(star_widget)
        star_layout.setContentsMargins(0, 0, 0, 0)
        star_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        star_layout.addWidget(star_btn)
        self.setItemWidget(item, COL_STAR, star_widget)

        # Title
        title_label = QLabel(task.title)
        title_label.setContentsMargins(8, 0, 8, 0)
        font = title_label.font()
        font.setPointSize(11)
        title_label.setFont(font)
        if task.starred:
            title_label.setStyleSheet(f"color: {COLOR_STARRED}; font-weight: bold; background: transparent;")
        else:
            title_label.setStyleSheet("background: transparent;")
        self.setItemWidget(item, COL_TITLE, title_label)

        # Date
        date_text = format_date_display(task.date)
        date_label = QLabel(date_text)
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = date_label.font()
        font.setPointSize(11)
        date_label.setFont(font)
        cls = get_date_class(task.date)
        if cls == "overdue":
            date_label.setStyleSheet(f"color: {COLOR_OVERDUE}; font-weight: bold; background: transparent;")
        elif cls == "future":
            date_label.setStyleSheet(f"color: {COLOR_FUTURE}; background: transparent;")
        else:
            date_label.setStyleSheet(f"color: {COLOR_TODAY}; background: transparent;")
        self.setItemWidget(item, COL_DATE, date_label)

        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 0, 2, 0)
        action_layout.setSpacing(4)

        btn_style = (
            "QPushButton { border: 1px solid #ccc; border-radius: 3px; padding: 2px 6px; "
            "background: #f5f5f5; font-size: 12px; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )
        tool_btn_style = (
            "QToolButton { border: 1px solid #ccc; border-radius: 3px; padding: 2px 6px; "
            "background: #f5f5f5; font-size: 12px; }"
            "QToolButton:hover { background: #e0e0e0; }"
            "QToolButton::menu-arrow { width: 8px; }"
            "QToolButton::menu-button { border-left: 1px solid #ccc; width: 12px; }"
        )

        inc_btn = QToolButton()
        inc_btn.setText("+1d")
        inc_btn.setFixedSize(52, 26)
        inc_btn.setStyleSheet(tool_btn_style)
        inc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        inc_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        inc_btn.clicked.connect(lambda checked, uri=task.uri: self.increment_requested.emit(uri))
        inc_menu = QMenu(inc_btn)
        inc_menu.setStyleSheet("QMenu::item { padding: 4px 16px; font-size: 11px; }")
        week_action = inc_menu.addAction("+1w")
        week_action.triggered.connect(lambda checked, uri=task.uri: self.increment_week_requested.emit(uri))
        month_action = inc_menu.addAction("+1m")
        month_action.triggered.connect(lambda checked, uri=task.uri: self.increment_month_requested.emit(uri))
        inc_btn.setMenu(inc_menu)
        action_layout.addWidget(inc_btn)

        today_btn = QPushButton("\U0001f4c5")
        today_btn.setFixedSize(30, 26)
        today_btn.setStyleSheet(btn_style)
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setToolTip("Set to today")
        today_btn.clicked.connect(lambda checked, uri=task.uri: self.today_requested.emit(uri))
        action_layout.addWidget(today_btn)

        edit_btn = QPushButton("\u270e")
        edit_btn.setFixedSize(30, 26)
        edit_btn.setStyleSheet(btn_style)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Edit task")
        edit_btn.clicked.connect(lambda checked, uri=task.uri: self.edit_requested.emit(uri))
        action_layout.addWidget(edit_btn)

        self.setItemWidget(item, COL_ACTIONS, action_widget)

        # Checkbox
        check_widget = QWidget()
        check_layout = QHBoxLayout(check_widget)
        check_layout.setContentsMargins(0, 0, 0, 0)
        check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check_box = QCheckBox()
        check_box.setToolTip("Complete (delete)")
        check_box.stateChanged.connect(lambda state, uri=task.uri: self.complete_toggled.emit(uri))
        check_layout.addWidget(check_box)
        self.setItemWidget(item, COL_DONE, check_widget)

        # Starred row background
        if task.starred:
            for col in range(5):
                item.setBackground(col, QColor("#f5eef8"))

    def _on_click(self, item, column):
        if column == COL_TITLE:
            uri = item.data(0, Qt.ItemDataRole.UserRole)
            if uri:
                self.edit_requested.emit(uri)
