"""
Ash Album — Standalone PDF viewer for file-association launch.

When the user double-clicks a PDF in Explorer, Windows passes the file
path as a command-line argument.  This module opens the PDF viewer
scoped to the containing folder so the user can navigate between PDFs.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from .config import AppConfig
from .pdf_viewer import PDFViewerWindow


class StandalonePDFViewer(QMainWindow):
    """
    Lightweight controller for opening a PDF via file-association
    (double-click in Explorer).

    Scans the containing folder for sibling PDFs and opens the
    full-featured PDFViewerWindow with navigation support.
    """

    def __init__(self, file_path: str, config: AppConfig):
        super().__init__()
        self.cfg = config
        self._file_path = os.path.abspath(file_path)

        self.setWindowTitle("Ash Album")
        self.hide()

        # Collect all PDFs in the same folder
        folder = Path(self._file_path).parent
        self._sibling_pdfs = self._scan_folder_pdfs(folder)

        # Launch viewer after the event loop starts
        QTimer.singleShot(50, self._launch_viewer)

    @staticmethod
    def _scan_folder_pdfs(folder: Path) -> list[str]:
        """Return all PDF file paths in *folder* (non-recursive),
        sorted alphabetically by name."""
        files: list[str] = []
        try:
            for f in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
                if f.is_file() and f.suffix.lower() == ".pdf":
                    files.append(str(f))
        except (PermissionError, OSError):
            pass
        return files

    def _launch_viewer(self):
        if not self._sibling_pdfs:
            QApplication.quit()
            return

        self._viewer = PDFViewerWindow(
            self._file_path,
            self._sibling_pdfs,
            None,
        )
        self._viewer.exec()
        QApplication.quit()
