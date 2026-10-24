from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


CALENDAR_STYLE = (
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


class EditDialog(QDialog):
    def __init__(self, title: str, date_str: str, note: str = "",
                 starred: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Task")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._result_title: str | None = None
        self._result_date: str | None = None
        self._result_note: str | None = None
        self._result_starred: bool = starred
        self._starred = starred
        self._setup_ui(title, date_str, note)

    def _setup_ui(self, title: str, date_str: str, note: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.title_edit = QLineEdit(title)
        self.title_edit.setStyleSheet(
            "padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px;"
        )
        self.title_edit.selectAll()

        # Star button next to the title field
        self.star_btn = QPushButton()
        self.star_btn.setFixedSize(22, 22)
        self.star_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.star_btn.setToolTip("Toggle priority")
        self.star_btn.clicked.connect(self._toggle_star)
        self._update_star_btn()

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(self.title_edit)
        title_row.addWidget(self.star_btn)
        form.addRow("Title:", title_row)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setStyleSheet(
            "QDateEdit { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }"
            "QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: right center;"
            "  width: 28px; border-left: 1px solid #ccc; }"
            "QDateEdit::down-arrow { width: 14px; height: 14px;"
            "  image: url(assets/dropdown_arrow.svg); }"
        )
        calendar = self.date_edit.calendarWidget()
        calendar.setStyleSheet(CALENDAR_STYLE)
        if date_str:
            parts = date_str.split("-")
            self.date_edit.setDate(date(int(parts[0]), int(parts[1]), int(parts[2])))
        else:
            self.date_edit.setDate(date.today())
        form.addRow("Due:", self.date_edit)

        self.note_edit = QTextEdit()
        self.note_edit.setPlainText(note)
        self.note_edit.setPlaceholderText("Optional note...")
        self.note_edit.setAcceptRichText(False)
        self.note_edit.setFixedHeight(175)
        self.note_edit.setStyleSheet(
            "QTextEdit { padding: 4px 8px; border: 1px solid #ccc; "
            "border-radius: 4px; font-size: 13px; }"
        )
        form.addRow("Note:", self.note_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(
            "QPushButton { padding: 8px 16px; border: 1px solid #ccc; "
            "border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.setStyleSheet(
            "QPushButton { background: #337ab7; color: white; padding: 8px 16px; "
            "border: none; border-radius: 4px; font-size: 13px; }"
            "QPushButton:hover { background: #286090; }"
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        self.title_edit.setFocus()

    def _update_star_btn(self):
        self.star_btn.setText("★" if self._starred else "☆")
        color = "#f0ad4e" if self._starred else "#bbb"
        self.star_btn.setStyleSheet(
            f"border: none; background: transparent; color: {color}; font-size: 16px;"
        )

    def _toggle_star(self):
        self._starred = not self._starred
        self._update_star_btn()

    def _save(self):
        title = self.title_edit.text().strip()
        if not title:
            return
        self._result_title = title
        self._result_date = self.date_edit.date().toString("yyyy-MM-dd")
        self._result_note = self.note_edit.toPlainText().strip()
        self._result_starred = self._starred
        self.accept()

    def get_result(self) -> tuple[str, str, str, bool] | None:
        if self._result_title is not None:
            return (self._result_title, self._result_date,
                    self._result_note, self._result_starred)
        return None
