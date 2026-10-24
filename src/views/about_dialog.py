import pathlib
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


REPO_URL = "https://github.com/Stefan-Schmidbauer/minitask"
MCP_URL = "https://github.com/Stefan-Schmidbauer/minitask-mcp"

LINK_STYLE = "color: #337ab7; text-decoration: none;"


class AboutDialog(QDialog):
    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About MiniTask")
        self.setModal(True)
        self.setFixedWidth(440)
        self.setStyleSheet("QDialog { background: white; }")
        self._setup_ui(version)

    def _setup_ui(self, version: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(6)

        # Logo
        icon_path = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "minitask.svg"
        pixmap = QPixmap(str(icon_path)).scaled(
            80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        icon_label = QLabel()
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        layout.addSpacing(4)

        name_label = QLabel("MiniTask")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #333;")
        layout.addWidget(name_label)

        # Version badge, linked to its release page when it is an exact release tag
        if re.fullmatch(r"v\d+\.\d+\.\d+", version):
            version_html = (
                f'<a href="{REPO_URL}/releases/tag/{version}" style="color: #555; '
                f'text-decoration: none;">Version {version}</a>'
            )
        else:
            version_html = f"Version {version}"
        version_label = QLabel(version_html)
        version_label.setOpenExternalLinks(True)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(
            "font-size: 12px; color: #555; background: #f0f0f0; "
            "border-radius: 9px; padding: 2px 10px;"
        )
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        badge_row.addWidget(version_label)
        badge_row.addStretch()
        layout.addLayout(badge_row)
        layout.addSpacing(8)

        tagline = QLabel("A lightweight CalDAV task manager.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(tagline)
        layout.addSpacing(10)

        # Links
        links = [
            ("GitHub", REPO_URL),
            ("Releases", f"{REPO_URL}/releases"),
            ("Report an issue", f"{REPO_URL}/issues"),
            ("MiniTask MCP", MCP_URL),
        ]
        links_label = QLabel(
            " &nbsp;·&nbsp; ".join(
                f'<a href="{url}" style="{LINK_STYLE}">{text}</a>' for text, url in links
            )
        )
        links_label.setOpenExternalLinks(True)
        links_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        links_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(links_label)
        layout.addSpacing(14)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #eee;")
        layout.addWidget(line)
        layout.addSpacing(6)

        # Footer
        footer = QLabel(
            "&copy; 2025–2026 Stefan Schmidbauer &amp; Claude (Anthropic)<br>"
            f'Released under the <a href="{REPO_URL}/blob/main/LICENSE" '
            f'style="{LINK_STYLE}">MIT License</a><br>'
            "Built with PySide6 (Qt6) and python-caldav"
        )
        footer.setOpenExternalLinks(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(footer)
        layout.addSpacing(12)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "QPushButton { background: #337ab7; color: white; padding: 8px 24px; "
            "border: none; border-radius: 4px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: #286090; }"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
