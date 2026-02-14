"""
Ash Album —  Full-screen image viewer with action buttons.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QPixmap, QKeySequence, QShortcut, QImage
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from .theme import COLORS


class ViewerWindow(QDialog):
    """Modal image/video-frame viewer with navigation and action buttons."""

    # Signals so the main window can react
    request_select = Signal(str)        # toggle selection
    request_crop = Signal(str)          # open crop dialog
    request_delete = Signal(str)        # delete
    request_hide = Signal(str)          # hide
    request_add_pdf = Signal(str)       # add to PDF selection
    item_removed = Signal(str)          # main window confirms removal
    closed = Signal()

    def __init__(
        self,
        items: list[str],
        start_index: int,
        selected_set: set[str],
        parent=None,
    ):
        # ── Initialise data BEFORE anything that can trigger resizeEvent ──
        self._items = items
        self._idx = max(0, min(start_index, len(items) - 1))
        self._selected = selected_set
        self._ready = False  # guard for resizeEvent

        super().__init__(parent)
        self.setWindowTitle("Ash Album — Viewer")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setMinimumSize(900, 620)

        self._build_ui()
        self._bind_shortcuts()

        # Mark ready *before* showMaximized so resizeEvent can work
        self._ready = True
        self.showMaximized()

        # Deferred first render — after layout is finalised and label has real size
        QTimer.singleShot(50, self._show_current)

    # ────────────────── UI ──────────────────

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- image area ---
        img_row = QHBoxLayout()
        img_row.setContentsMargins(0, 0, 0, 0)

        self._btn_prev = self._nav_btn("❮")
        self._btn_prev.clicked.connect(self._prev)
        img_row.addWidget(self._btn_prev)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._image_label.setStyleSheet("background-color: transparent;")
        img_row.addWidget(self._image_label, 1)

        self._btn_next = self._nav_btn("❯")
        self._btn_next.clicked.connect(self._next)
        img_row.addWidget(self._btn_next)

        root.addLayout(img_row, 1)

        # --- info bar ---
        self._info_label = QLabel()
        self._info_label.setObjectName("dimLabel")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setFixedHeight(28)
        self._info_label.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_dim']}; font-size: 11px;"
        )
        root.addWidget(self._info_label)

        # --- action bar ---
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background-color: {COLORS['bg_mid']};")
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(16, 0, 16, 0)
        bar_lay.setSpacing(12)

        self._btn_select = self._action_btn("Select", "accentBtn")
        self._btn_select.clicked.connect(self._on_select)

        self._btn_crop = self._action_btn("Crop")
        self._btn_crop.clicked.connect(self._on_crop)

        self._btn_delete = self._action_btn("Delete", "dangerBtn")
        self._btn_delete.clicked.connect(self._on_delete)

        self._btn_hide = self._action_btn("Hide")
        self._btn_hide.clicked.connect(self._on_hide)

        self._btn_pdf = self._action_btn("Add to PDF", "successBtn")
        self._btn_pdf.clicked.connect(self._on_add_pdf)

        bar_lay.addStretch()
        for b in (self._btn_select, self._btn_crop, self._btn_delete,
                  self._btn_hide, self._btn_pdf):
            bar_lay.addWidget(b)
        bar_lay.addStretch()

        root.addWidget(bar)

    # ────────────────── helpers ──────────────────

    @staticmethod
    def _nav_btn(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedWidth(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_dim']}; "
            f"font-size: 26px; border: none; }}"
            f"QPushButton:hover {{ color: {COLORS['text']}; "
            f"background: {COLORS['bg_mid']}; }}"
        )
        return btn

    @staticmethod
    def _action_btn(text: str, obj_name: str | None = None) -> QPushButton:
        btn = QPushButton(text)
        if obj_name:
            btn.setObjectName(obj_name)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(36)
        return btn

    def _bind_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._prev)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._next)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)

    # ────────────────── display ──────────────────

    def _current_path(self) -> str | None:
        if 0 <= self._idx < len(self._items):
            return self._items[self._idx]
        return None

    def _show_current(self):
        if not self._ready:
            return

        path = self._current_path()
        if not path:
            self._image_label.setText("No image")
            return

        ext = Path(path).suffix.lower()
        from .config import VIDEO_EXTENSIONS

        if ext in VIDEO_EXTENSIONS:
            pm = self._video_frame(path)
        else:
            pm = QPixmap(path)

        if pm and not pm.isNull():
            label_size = self._image_label.size()
            if label_size.width() > 10 and label_size.height() > 10:
                scaled = pm.scaled(
                    label_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._image_label.setPixmap(scaled)
            else:
                self._image_label.setPixmap(pm)
        else:
            self._image_label.setText("Cannot load file")

        # Info
        try:
            p = Path(path)
            sz = p.stat().st_size
            nice = self._nice_size(sz)
            self._info_label.setText(
                f"{p.name}   •   {nice}   •   "
                f"{self._idx + 1} / {len(self._items)}"
            )
        except OSError:
            self._info_label.setText(Path(path).name)

        # Update select button label
        is_sel = path in self._selected
        self._btn_select.setText("Deselect ✓" if is_sel else "Select")

        # Disable crop for videos
        self._btn_crop.setEnabled(ext not in VIDEO_EXTENSIONS)

    @staticmethod
    def _video_frame(path: str) -> QPixmap | None:
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                return None
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            qimg = QImage(frame.data, w, h, w * ch, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception:
            return None

    @staticmethod
    def _nice_size(b: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {u}" if u != "B" else f"{b} {u}"
            b /= 1024
        return f"{b:.1f} TB"

    # ────────────────── navigation ──────────────────

    def _prev(self):
        if self._idx > 0:
            self._idx -= 1
            self._show_current()

    def _next(self):
        if self._idx < len(self._items) - 1:
            self._idx += 1
            self._show_current()

    # ────────────────── actions ──────────────────

    def _on_select(self):
        path = self._current_path()
        if path:
            self.request_select.emit(path)
            # Toggle locally so UI updates immediately
            if path in self._selected:
                self._selected.discard(path)
            else:
                self._selected.add(path)
            self._show_current()

    def _on_crop(self):
        path = self._current_path()
        if path:
            self.request_crop.emit(path)

    def _on_delete(self):
        path = self._current_path()
        if path:
            self.request_delete.emit(path)
            # The main window calls confirm_removal() if it succeeded

    def _on_hide(self):
        path = self._current_path()
        if path:
            self.request_hide.emit(path)
            # The main window calls confirm_removal() if it succeeded

    def confirm_removal(self, path: str):
        """Called by the main window after a successful delete / hide."""
        if path in self._items:
            idx = self._items.index(path)
            self._items.pop(idx)
            if self._idx >= len(self._items):
                self._idx = max(0, len(self._items) - 1)
            if self._items:
                self._show_current()
            else:
                self.close()

    def _on_add_pdf(self):
        path = self._current_path()
        if path:
            self.request_add_pdf.emit(path)
            if path not in self._selected:
                self._selected.add(path)
            self._show_current()

    # ────────────────── resize ──────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._ready:
            self._show_current()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
