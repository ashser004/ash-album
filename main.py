"""
Ash Album — Entry point.

Usage:
    python main.py
    pyinstaller --onefile --windowed main.py
"""

import sys
import os

# Suppress noisy FFmpeg / OpenCV warnings in the console
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg.warning=false"

# Ensure the project root is on the path so ``src`` package resolves
# when running from source or from a PyInstaller bundle.
if getattr(sys, "frozen", False):
    _BASE = sys._MEIPASS  # type: ignore[attr-defined]
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from src.config import AppConfig, ALL_EXTENSIONS, PDF_EXTENSIONS
from src.theme import get_stylesheet
from src.first_run import FirstRunDialog
from src.main_window import MainWindow


def _get_file_arg():
    """Return an absolute image/video path from sys.argv, or None."""
    if len(sys.argv) < 2:
        return None
    candidate = sys.argv[1]
    if os.path.isfile(candidate):
        ext = os.path.splitext(candidate)[1].lower()
        if ext in ALL_EXTENSIONS:
            return os.path.abspath(candidate)
    return None


def _get_pdf_arg():
    """Return an absolute PDF path from sys.argv, or None."""
    if len(sys.argv) < 2:
        return None
    candidate = sys.argv[1]
    if os.path.isfile(candidate):
        ext = os.path.splitext(candidate)[1].lower()
        if ext in PDF_EXTENSIONS:
            return os.path.abspath(candidate)
    return None


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Ash Album")
    app.setApplicationVersion("1.1.2")
    app.setStyle("Fusion")  # consistent look on all Windows builds

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply dark theme
    app.setStyleSheet(get_stylesheet())

    # App icon (place icon.png in project root — 256×256 recommended)
    icon_path = os.path.join(_BASE, "icon.png")
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Check for file-association launch (double-click an image/video in Explorer)
    file_arg = _get_file_arg()
    pdf_arg = _get_pdf_arg()

    # Configuration
    config = AppConfig()
    if file_arg:
        # Standalone viewer mode — silently ensure config exists
        if not config.is_first_run():
            config.load()
        config.save()

        from src.standalone_viewer import StandaloneViewer
        controller = StandaloneViewer(file_arg, config)
    elif pdf_arg:
        # Standalone PDF viewer mode
        if not config.is_first_run():
            config.load()
        config.save()

        from src.standalone_pdf_viewer import StandalonePDFViewer
        controller = StandalonePDFViewer(pdf_arg, config)
    else:
        # Normal gallery mode
        if config.is_first_run():
            dlg = FirstRunDialog(config)
            if dlg.exec() == 0:  # rejected / closed
                sys.exit(0)
        else:
            config.load()
            config.save()  # ensure dirs exist

        # Main window
        window = MainWindow(config)
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
