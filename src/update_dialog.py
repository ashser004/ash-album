"""
Ash Album — Update available dialog with download/install flow.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .config import APP_NAME, APP_VERSION
from .theme import COLORS
from .update_manager import (
    DEFAULT_INSTALLER_NAME,
    UpdateDownloadWorker,
    UpdateManifest,
    cleanup_download_cache,
    launch_installer,
)


class UpdateDialog(QDialog):
    def __init__(self, manifest: UpdateManifest, download_dir: str | Path, parent=None):
        super().__init__(parent)
        self._manifest = manifest
        self._download_dir = Path(download_dir)
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._downloaded_path = self._download_dir / self._download_filename()
        self._download_worker: UpdateDownloadWorker | None = None
        self._download_complete = self._downloaded_path.exists()
        self._cleanup_attempts = 0
        self._cleanup_max_attempts = 6

        self.setWindowTitle(f"{APP_NAME} Update")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setMinimumWidth(440)
        self._build_ui()
        self._sync_state()

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel(f"{APP_NAME} {self._manifest.version} is available")
        title.setWordWrap(True)
        title.setObjectName("titleLabel")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: 800;")
        root.addWidget(title)

        body = QLabel(
            f"Current version: {APP_VERSION}\n"
            f"Latest version: {self._manifest.version}\n\n"
            "The update will be downloaded to the app storage and then launched so you can install it immediately."
        )
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        root.addWidget(body)

        self._status = QLabel("Ready to download")
        self._status.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; font-weight: 600;")
        root.addWidget(self._status)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setTextVisible(True)
        self._progress.setRange(0, 0)
        root.addWidget(self._progress)

        self._download_btn = QPushButton()
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.setFixedHeight(38)
        self._download_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent']}; color: #ffffff; "
            f"border: none; border-radius: 8px; padding: 6px 18px; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}"
            f"QPushButton:disabled {{ background-color: {COLORS['bg_mid']}; color: {COLORS['text_dim']}; }}"
        )
        self._download_btn.clicked.connect(self._on_primary_action)

        self._close_btn = QPushButton("Later")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setFixedHeight(38)
        self._close_btn.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addWidget(self._close_btn)
        button_row.addWidget(self._download_btn, 1)
        root.addLayout(button_row)

        self._cleanup_retry_timer = QTimer(self)
        self._cleanup_retry_timer.setInterval(10000)
        self._cleanup_retry_timer.timeout.connect(self._retry_cleanup_after_install)

    def _download_filename(self) -> str:
        name = Path(urlparse(self._manifest.download_url).path).name.strip()
        return name or DEFAULT_INSTALLER_NAME

    def _sync_state(self):
        if self._download_complete and self._downloaded_path.exists():
            self._status.setText("Installer already downloaded")
            self._download_btn.setText(f"Install {self._manifest.version}")
        else:
            self._download_btn.setText(f"Download {self._manifest.version}")

    def _on_primary_action(self):
        if self._download_complete and self._downloaded_path.exists():
            self._launch_installer()
            return
        self._start_download()

    def _start_download(self):
        if self._download_worker and self._download_worker.isRunning():
            return

        self._status.setText("Downloading update...")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._download_btn.setEnabled(False)

        self._download_worker = UpdateDownloadWorker(
            self._manifest.download_url,
            self._downloaded_path,
            self,
        )
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(downloaded)
            self._progress.setFormat(f"%v / %m bytes")
        else:
            self._progress.setRange(0, 0)
            self._progress.setFormat("Downloading...")

    def _on_download_finished(self, downloaded_path: str):
        self._downloaded_path = Path(downloaded_path)
        self._download_complete = True
        self._status.setText("Download complete. You can install now.")
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._progress.setFormat("Done")
        self._download_btn.setEnabled(True)
        self._download_btn.setText(f"Install {self._manifest.version}")

    def _on_download_failed(self, message: str):
        self._status.setText("Download failed")
        self._progress.setVisible(False)
        self._download_btn.setEnabled(True)
        QMessageBox.warning(self, "Update Download Failed", message)

    def _launch_installer(self):
        if not self._downloaded_path.exists():
            self._download_complete = False
            self._sync_state()
            self._start_download()
            return

        if not launch_installer(self._downloaded_path):
            QMessageBox.warning(
                self,
                "Could Not Launch Installer",
                f"Ash Album could not launch:\n{self._downloaded_path}",
            )
            return

        self._status.setText("Launching installer...")
        self._download_btn.setEnabled(False)
        self._close_btn.setEnabled(False)
        self.hide()
        self._cleanup_attempts = 0
        self._cleanup_retry_timer.start()
        QTimer.singleShot(1000, self._retry_cleanup_after_install)

    def _retry_cleanup_after_install(self):
        cleanup_download_cache(self._download_dir, remove_installers=True)
        try:
            if self._downloaded_path.exists():
                self._downloaded_path.unlink()
        except OSError:
            pass

        if not self._downloaded_path.exists():
            self._cleanup_retry_timer.stop()
            self.accept()
            return

        self._cleanup_attempts += 1
        if self._cleanup_attempts >= self._cleanup_max_attempts:
            self._cleanup_retry_timer.stop()
            self.accept()

    def closeEvent(self, event):
        self._cleanup_retry_timer.stop()
        cleanup_download_cache(self._download_dir, remove_installers=False)
        super().closeEvent(event)
