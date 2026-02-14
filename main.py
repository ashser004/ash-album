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
from PySide6.QtGui import QFont

from src.config import AppConfig
from src.theme import get_stylesheet
from src.first_run import FirstRunDialog
from src.main_window import MainWindow


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Ash Album")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")  # consistent look on all Windows builds

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply dark theme
    app.setStyleSheet(get_stylesheet())

    # Configuration
    config = AppConfig()
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
