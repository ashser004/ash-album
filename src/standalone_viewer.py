"""
Ash Album — Standalone viewer for file-association launch.

When the user double-clicks an image in Explorer, Windows passes the
file path as a command-line argument.  This module opens the full-featured
viewer scoped to the containing folder.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
)

from .config import ALL_EXTENSIONS, IMAGE_EXTENSIONS, AppConfig
from .crop_widget import CropDialog
from .media_ops import MediaOperations
from .pdf_export import auto_filename, generate_pdf
from .viewer_window import ViewerWindow


class StandaloneViewer(QMainWindow):
    """
    Lightweight controller for opening a single image/video via
    file-association (double-click in Explorer).

    Scans only the containing folder and opens the full-featured
    ViewerWindow for navigation and actions.
    """

    def __init__(self, file_path: str, config: AppConfig):
        super().__init__()
        self.cfg = config
        self._file_path = os.path.abspath(file_path)
        self._selected_paths: list[str] = []
        self._ops = MediaOperations(self.cfg.hidden_dir)

        self.setWindowTitle("Ash Album")
        self.hide()

        # Collect all media files from the same folder
        folder = Path(self._file_path).parent
        self._all_paths = self._scan_folder(folder)

        # Find start index (case-insensitive on Windows)
        norm = os.path.normcase(os.path.abspath(self._file_path))
        self._start_idx = 0
        for i, p in enumerate(self._all_paths):
            if os.path.normcase(os.path.abspath(p)) == norm:
                self._start_idx = i
                break

        # Launch viewer after the event loop starts
        QTimer.singleShot(50, self._launch_viewer)

    # ── folder scanning ──────────────────────────────────────────

    @staticmethod
    def _scan_folder(folder: Path) -> list[str]:
        """Return all image/video file paths in *folder* (non-recursive),
        sorted alphabetically by name."""
        files: list[str] = []
        try:
            for f in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
                if f.is_file() and f.suffix.lower() in ALL_EXTENSIONS:
                    files.append(str(f))
        except (PermissionError, OSError):
            pass
        return files

    # ── viewer lifecycle ─────────────────────────────────────────

    def _launch_viewer(self):
        if not self._all_paths:
            QApplication.quit()
            return

        self._viewer = ViewerWindow(
            self._all_paths,
            self._start_idx,
            self._selected_paths,
            None,
        )
        self._viewer.request_select.connect(self._toggle_select)
        self._viewer.request_crop.connect(self._do_crop)
        self._viewer.request_delete.connect(self._do_delete)
        self._viewer.request_hide.connect(self._do_hide)
        self._viewer.request_generate_pdf.connect(self._generate_pdf)

        # Show standalone-only controls (Generate PDF button)
        self._viewer.set_standalone_mode(True)

        self._viewer.exec()
        QApplication.quit()

    # ── signal handlers ──────────────────────────────────────────

    def _toggle_select(self, path: str):
        if path in self._selected_paths:
            self._selected_paths.remove(path)
        else:
            self._selected_paths.append(path)

    def _do_crop(self, path: str):
        dlg = CropDialog(path, self._viewer)
        dlg.cropped.connect(self._on_cropped)
        dlg.exec()

    def _on_cropped(self, saved_path: str):
        # If it's a new file in the same folder, add to viewer's navigation list
        if saved_path not in self._all_paths:
            saved_folder = str(Path(saved_path).parent)
            orig_folder = str(Path(self._file_path).parent)
            if os.path.normcase(saved_folder) == os.path.normcase(orig_folder):
                self._all_paths.append(saved_path)
                self._all_paths.sort(key=lambda x: Path(x).name.lower())
                # Update viewer's internal list
                self._viewer._items = list(self._all_paths)
        # Refresh current view (file may have been overwritten)
        self._viewer._show_current()

    def _do_delete(self, path: str):
        ok = self._ops.delete_to_trash(path)
        if ok:
            self._viewer.confirm_removal(path)
            if path in self._selected_paths:
                self._selected_paths.remove(path)
            if path in self._all_paths:
                self._all_paths.remove(path)

    def _do_hide(self, path: str):
        new_path = self._ops.hide_file(path)
        if new_path:
            self._viewer.confirm_removal(path)
            if path in self._selected_paths:
                self._selected_paths.remove(path)
            if path in self._all_paths:
                self._all_paths.remove(path)

    # ── PDF generation ───────────────────────────────────────────

    def _generate_pdf(self):
        img_exts = IMAGE_EXTENSIONS
        images = [
            p for p in self._selected_paths
            if Path(p).suffix.lower() in img_exts and Path(p).exists()
        ]
        if not images:
            QMessageBox.information(
                self._viewer,
                "No Images",
                "Select at least one image to generate a PDF.\n\n"
                "Tip: Use the Select button to pick images.",
            )
            return

        # Ask page size
        page_mode = self._ask_page_size()
        if not page_mode:
            return

        default_name = auto_filename()
        save_path, _ = QFileDialog.getSaveFileName(
            self._viewer,
            "Save PDF",
            str(Path.home() / "Downloads" / default_name),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return
        if not Path(save_path).stem:
            save_path = str(Path(save_path).parent / default_name)

        try:
            total = len(images)
            cancelled = False

            progress = QProgressDialog(
                f"Generating PDF... (0/{total})",
                "Cancel",
                0, total, self._viewer,
            )
            progress.setWindowTitle("Generating PDF")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setMinimumWidth(400)
            progress.show()
            QApplication.processEvents()

            def _on_progress(current: int, total_count: int) -> bool:
                nonlocal cancelled
                if progress.wasCanceled():
                    cancelled = True
                    return False
                pct = int((current / total_count) * 100) if total_count else 0
                progress.setLabelText(
                    f"Please wait while generating PDF... ({pct}%)\n"
                    f"Processing image {current + 1} of {total_count}"
                )
                progress.setValue(current)
                QApplication.processEvents()
                return True

            generate_pdf(images, save_path, page_mode=page_mode,
                         progress_callback=_on_progress)
            progress.setValue(total)
            progress.close()

            if cancelled:
                pass  # silently cancelled
            else:
                QMessageBox.information(
                    self._viewer,
                    "PDF Created",
                    f"Saved {len(images)} image(s) to:\n{save_path}",
                )
        except Exception as exc:
            QMessageBox.warning(
                self._viewer, "Error", f"PDF generation failed:\n{exc}"
            )

    def _ask_page_size(self) -> str | None:
        """Show dialog to choose PDF page size. Returns 'a4', 'default', or None."""
        msg = QMessageBox(self._viewer)
        msg.setWindowTitle("PDF Page Size")
        msg.setText("Choose the PDF page size:")
        msg.setInformativeText(
            "A4 \u2014 Each image is scaled to fit a standard A4 page "
            "(210 \u00d7 297 mm). Ideal for printing.\n\n"
            "Default \u2014 Each page matches the original image dimensions. "
            "Best for digital viewing at full quality."
        )
        btn_a4 = msg.addButton("A4", QMessageBox.ButtonRole.AcceptRole)
        btn_default = msg.addButton("Default", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_a4:
            return "a4"
        if clicked == btn_default:
            return "default"
        return None
