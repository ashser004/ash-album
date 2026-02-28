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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import AppConfig
from .default_app import is_default_for_images, open_default_apps_settings
from .theme import COLORS


class FirstRunDialog(QDialog):
    """Shown once on first launch so the user can confirm / change the
    base data folder, then optionally set the app as the default image
    viewer."""

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Welcome to Ash Album")
        self.setFixedSize(520, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._pages = QStackedWidget()
        root.addWidget(self._pages)

        # Page 0 – folder selection (existing flow)
        self._pages.addWidget(self._build_folder_page())

        # Page 1 – set-as-default prompt
        self._pages.addWidget(self._build_default_page())

    # ---- page 0: folder selection ----

    def _build_folder_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(36, 32, 36, 28)
        lay.setSpacing(12)

        title = QLabel("ASH ALBUM")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel("Your private desktop gallery")
        sub.setObjectName("subtitleLabel")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        lay.addSpacing(18)

        info = QLabel(
            "Ash Album stores thumbnail cache, hidden files and\n"
            "temporary data in a local folder. You can change the\n"
            "location below or keep the default."
        )
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        lay.addWidget(info)

        lay.addSpacing(10)

        self._path_label = QLabel(str(self.config.base_dir))
        self._path_label.setAlignment(Qt.AlignCenter)
        self._path_label.setStyleSheet(
            f"background-color: {COLORS['bg_light']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; padding: 10px; font-size: 12px;"
        )
        self._path_label.setWordWrap(True)
        lay.addWidget(self._path_label)

        change_btn = QPushButton("Change Folder")
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.clicked.connect(self._pick_folder)
        change_btn.setFixedWidth(160)
        h = QHBoxLayout()
        h.addStretch()
        h.addWidget(change_btn)
        h.addStretch()
        lay.addLayout(h)

        lay.addStretch()

        next_btn = QPushButton("  Continue  ")
        next_btn.setObjectName("accentBtn")
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        next_btn.setFixedHeight(44)
        next_btn.clicked.connect(self._go_to_default_page)
        lay.addWidget(next_btn, alignment=Qt.AlignCenter)

        return page

    # ---- page 1: set-as-default ----

    def _build_default_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(36, 32, 36, 28)
        lay.setSpacing(14)

        title = QLabel("SET AS DEFAULT")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        lay.addSpacing(8)

        desc = QLabel(
            "Would you like to set Ash Album as the default app for\n"
            "opening JPG, JPEG, and PNG images?\n\n"
            "This means double-clicking an image file will open it\n"
            "directly in Ash Album."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 13px;")
        lay.addWidget(desc)

        lay.addSpacing(6)

        ext_label = QLabel("📷  .jpg   .jpeg   .png")
        ext_label.setAlignment(Qt.AlignCenter)
        ext_label.setStyleSheet(
            f"background-color: {COLORS['bg_light']}; "
            f"border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; padding: 14px; font-size: 14px; "
            f"font-weight: 600; letter-spacing: 2px;"
        )
        lay.addWidget(ext_label)

        lay.addStretch()

        # ---- Yes / No buttons ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        skip_btn = QPushButton("  No, Thanks  ")
        skip_btn.setCursor(Qt.PointingHandCursor)
        skip_btn.setFixedHeight(44)
        skip_btn.setFont(QFont("Segoe UI", 12))
        skip_btn.clicked.connect(self._finish_skip_default)
        btn_row.addWidget(skip_btn)

        yes_btn = QPushButton("  Yes, Set Default  ")
        yes_btn.setObjectName("accentBtn")
        yes_btn.setCursor(Qt.PointingHandCursor)
        yes_btn.setFixedHeight(44)
        yes_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        yes_btn.clicked.connect(self._finish_set_default)
        btn_row.addWidget(yes_btn)

        lay.addLayout(btn_row)

        return page

    # ---- actions ----

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select data folder", str(self.config.base_dir)
        )
        if folder:
            self.config.set_base_dir(folder)
            self._path_label.setText(str(self.config.base_dir))

    def _go_to_default_page(self):
        """Save config after folder step, then show default-app page."""
        self.config.save()
        # If already the default, skip straight to finish
        if is_default_for_images():
            self.config.default_app_asked = True
            self.config.save()
            self.accept()
            return
        self._pages.setCurrentIndex(1)

    def _finish_skip_default(self):
        self.config.default_app_asked = True
        self.config.save()
        self.accept()

    def _finish_set_default(self):
        self.config.default_app_asked = True
        self.config.save()
        open_default_apps_settings()
        self.accept()
