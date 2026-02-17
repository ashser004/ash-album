"""
Ash Album —  Full-screen media viewer with action buttons and video playback.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize, QTimer, QUrl
from PySide6.QtGui import QFont, QPixmap, QKeySequence, QShortcut, QImage
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from .config import VIDEO_EXTENSIONS
from .theme import COLORS


class ViewerWindow(QDialog):
    """Modal image/video viewer with navigation and action buttons."""

    # Signals so the main window can react
    request_select = Signal(str)        # toggle selection
    request_crop = Signal(str)          # open crop dialog
    request_delete = Signal(str)        # delete
    request_hide = Signal(str)          # hide
    request_add_pdf = Signal(str)       # add to PDF selection
    closed = Signal()

    def __init__(
        self,
        items: list[str],
        start_index: int,
        selected_list: list[str],
        parent=None,
    ):
        # ── Initialise data BEFORE anything that can trigger resizeEvent ──
        self._items = items
        self._idx = max(0, min(start_index, len(items) - 1))
        self._selected = selected_list
        self._ready = False  # guard for resizeEvent
        self._current_pixmap: QPixmap | None = None
        self._is_video = False

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

        # --- media area ---
        media_row = QHBoxLayout()
        media_row.setContentsMargins(0, 0, 0, 0)

        self._btn_prev = self._nav_btn("❮")
        self._btn_prev.clicked.connect(self._prev)
        media_row.addWidget(self._btn_prev)

        # Stacked widget: page 0 = image, page 1 = video
        self._media_stack = QStackedWidget()
        self._media_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Page 0: image label
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._image_label.setStyleSheet("background-color: transparent;")
        self._media_stack.addWidget(self._image_label)

        # Page 1: video widget
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background-color: black;")
        self._media_stack.addWidget(self._video_widget)

        # Media player
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.errorOccurred.connect(self._on_media_error)

        media_row.addWidget(self._media_stack, 1)

        self._btn_next = self._nav_btn("❯")
        self._btn_next.clicked.connect(self._next)
        media_row.addWidget(self._btn_next)

        root.addLayout(media_row, 1)

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
        bar.setFixedHeight(60)
        bar.setStyleSheet(
            f"background-color: {COLORS['bg_dark']};"
            f"border-top: 1px solid {COLORS['border']};"
        )
        bar_lay = QHBoxLayout(bar)
        bar_lay.setContentsMargins(20, 0, 20, 0)
        bar_lay.setSpacing(14)

        # ── button factory with explicit per-button colours ──
        _S = self._viewer_btn

        self._btn_select = _S("Select", bg="#7c5cfc", hover="#9b7dff")
        self._btn_select.setMinimumWidth(100)  # Ensure minimum width for changing text
        self._btn_select.clicked.connect(self._on_select)

        self._btn_crop = _S("Crop", bg="#3d5afe", hover="#536dfe")
        self._btn_crop.clicked.connect(self._on_crop)

        self._btn_play = _S("⏸  Pause", bg="#00bfa5", hover="#1de9b6")
        self._btn_play.clicked.connect(self._toggle_play_pause)
        self._btn_play.hide()

        self._btn_delete = _S("Delete", bg="#ef5350", hover="#f44336")
        self._btn_delete.clicked.connect(self._on_delete)

        self._btn_hide = _S("Hide", bg="#ff9800", hover="#ffb74d")
        self._btn_hide.clicked.connect(self._on_hide)

        self._btn_pdf = _S("Add to PDF", bg="#43c667", hover="#50d870")
        self._btn_pdf.clicked.connect(self._on_add_pdf)

        bar_lay.addStretch()
        for b in (self._btn_select, self._btn_crop, self._btn_play,
                  self._btn_delete, self._btn_hide, self._btn_pdf):
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

    @staticmethod
    def _viewer_btn(text: str, bg: str, hover: str) -> QPushButton:
        """Create a high-contrast action button with explicit colours."""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(38)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: #ffffff; "
            f"border: none; border-radius: 8px; padding: 6px 22px; "
            f"font-weight: 700; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {hover}; }}"
            f"QPushButton:pressed {{ opacity: 0.8; }}"
        )
        return btn

    def _bind_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._prev)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._next)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._toggle_play_pause)

    # ────────────────── display ──────────────────

    def _current_path(self) -> str | None:
        if 0 <= self._idx < len(self._items):
            return self._items[self._idx]
        return None

    def _show_current(self):
        if not self._ready:
            return

        # Stop any existing playback
        self._media_player.stop()

        path = self._current_path()
        if not path:
            self._image_label.setText("No image")
            return

        ext = Path(path).suffix.lower()
        self._is_video = ext in VIDEO_EXTENSIONS

        if self._is_video:
            self._show_video(path)
        else:
            self._show_image(path)

        # Info bar
        self._update_info(path)

        # Button states
        is_sel = path in self._selected
        if is_sel:
            page_num = self._selected.index(path) + 1
            self._btn_select.setText(f"Deselect ✓  (Page {page_num})")
        else:
            self._btn_select.setText("Select")
        self._btn_crop.setVisible(not self._is_video)
        self._btn_play.setVisible(self._is_video)

    def _show_image(self, path: str):
        self._media_stack.setCurrentIndex(0)
        pm = QPixmap(path)
        if pm and not pm.isNull():
            self._current_pixmap = pm
            self._scale_image()
        else:
            self._current_pixmap = None
            self._image_label.setText("Cannot load file")

    def _scale_image(self):
        """Scale and display the cached pixmap to fit the image label."""
        if not self._current_pixmap:
            return
        label_size = self._image_label.size()
        if label_size.width() > 10 and label_size.height() > 10:
            scaled = self._current_pixmap.scaled(
                label_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)
        else:
            self._image_label.setPixmap(self._current_pixmap)

    def _show_video(self, path: str):
        self._current_pixmap = None
        self._media_stack.setCurrentIndex(1)
        self._media_player.setSource(QUrl.fromLocalFile(path))
        self._media_player.play()
        self._btn_play.setText("⏸  Pause")

    def _toggle_play_pause(self):
        if not self._is_video:
            return
        state = self._media_player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
            self._btn_play.setText("▶  Play")
        else:
            self._media_player.play()
            self._btn_play.setText("⏸  Pause")

    def _on_media_error(self, error, message):
        """If video playback fails, fall back to a static frame."""
        path = self._current_path()
        if not path:
            return
        self._media_stack.setCurrentIndex(0)
        pm = self._video_frame(path)
        if pm and not pm.isNull():
            self._current_pixmap = pm
            self._scale_image()
        else:
            self._image_label.setText(f"Cannot play video: {message}")

    def _update_info(self, path: str):
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
            # The shared _selected set is toggled by main window synchronously;
            # just refresh the UI to reflect the new state.
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
        if not path:
            return
        # Only images can be added to PDF
        if self._is_video:
            return
        self.request_add_pdf.emit(path)
        if path not in self._selected:
            self._selected.append(path)
        self._show_current()

    # ────────────────── resize ──────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._ready:
            return
        # Only re-scale images; video widget auto-resizes
        if not self._is_video and self._current_pixmap:
            self._scale_image()

    def closeEvent(self, event):
        self._media_player.stop()
        self.closed.emit()
        super().closeEvent(event)
