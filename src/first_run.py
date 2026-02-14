"""
Ash Album — First-run welcome / setup dialog.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .config import AppConfig
from .theme import COLORS


class FirstRunDialog(QDialog):
    """Shown once on first launch so the user can confirm / change the
    base data folder."""

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Welcome to Ash Album")
        self.setFixedSize(520, 380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 28)
        root.setSpacing(12)

        # Title
        title = QLabel("ASH ALBUM")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # Subtitle
        sub = QLabel("Your private desktop gallery")
        sub.setObjectName("subtitleLabel")
        sub.setAlignment(Qt.AlignCenter)
        root.addWidget(sub)

        root.addSpacing(18)

        # Explanation
        info = QLabel(
            "Ash Album stores thumbnail cache, hidden files and\n"
            "temporary data in a local folder. You can change the\n"
            "location below or keep the default."
        )
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        root.addWidget(info)

        root.addSpacing(10)

        # Folder path
        self._path_label = QLabel(str(self.config.base_dir))
        self._path_label.setAlignment(Qt.AlignCenter)
        self._path_label.setStyleSheet(
            f"background-color: {COLORS['bg_light']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; padding: 10px; font-size: 12px;"
        )
        self._path_label.setWordWrap(True)
        root.addWidget(self._path_label)

        # Change folder button
        change_btn = QPushButton("Change Folder")
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.clicked.connect(self._pick_folder)
        change_btn.setFixedWidth(160)
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(change_btn)
        h_layout.addStretch()
        root.addLayout(h_layout)

        root.addStretch()

        # Get started
        start_btn = QPushButton("  Get Started  ")
        start_btn.setObjectName("accentBtn")
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        start_btn.setFixedHeight(44)
        start_btn.clicked.connect(self._finish)
        root.addWidget(start_btn, alignment=Qt.AlignCenter)

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select data folder", str(self.config.base_dir)
        )
        if folder:
            self.config.set_base_dir(folder)
            self._path_label.setText(str(self.config.base_dir))

    def _finish(self):
        self.config.save()
        self.accept()
