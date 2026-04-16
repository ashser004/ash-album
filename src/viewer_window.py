"""
Ash Album —  Full-screen media viewer with action buttons and video playback.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize, QTimer, QUrl, QEvent
from PySide6.QtGui import QFont, QPixmap, QKeySequence, QShortcut, QImage
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from .config import VIDEO_EXTENSIONS
from .media_ops import copy_files_to_clipboard
from .theme import COLORS


class ViewerWindow(QDialog):
    """Modal image/video viewer with navigation and action buttons."""

    # Signals so the main window can react
    request_select = Signal(str)        # toggle selection
    request_crop = Signal(str)          # open crop dialog
    request_rotate = Signal(str)        # rotate image 90° clockwise
    request_delete = Signal(str)        # delete
    request_hide = Signal(str)          # hide
    request_generate_pdf = Signal()     # generate PDF (standalone mode)
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
        self._video_widget = None
        self._media_player = None
        self._audio_output = None
        self._copy_feedback_active = False
        self._copy_button_text = "Copy"
        self._zoom_factor = 1.0
        self._pinch_base_zoom = 1.0
        self._zoom_min = 0.25
        self._zoom_max = 6.0

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

        self._copy_feedback_timer = QTimer(self)
        self._copy_feedback_timer.setSingleShot(True)
        self._copy_feedback_timer.timeout.connect(self._restore_copy_button)

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
        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(False)
        self._image_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_scroll.setStyleSheet("background-color: transparent; border: none;")
        self._image_scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._image_scroll.viewport().grabGesture(Qt.GestureType.PinchGesture)
        self._image_scroll.viewport().installEventFilter(self)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._image_label.setStyleSheet("background-color: transparent;")
        self._image_scroll.setWidget(self._image_label)
        self._media_stack.addWidget(self._image_scroll)

        # Page 1: video placeholder (real QtMultimedia widgets are created on demand)
        self._video_page = QWidget()
        self._video_page.setStyleSheet("background-color: black;")
        self._video_layout = QVBoxLayout(self._video_page)
        self._video_layout.setContentsMargins(0, 0, 0, 0)
        self._video_layout.setSpacing(0)
        self._media_stack.addWidget(self._video_page)

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

        self._btn_rotate = _S("↻", bg="#1f8fff", hover="#47a4ff")
        self._btn_rotate.setToolTip("Rotate 90°")
        self._btn_rotate.clicked.connect(self._on_rotate)
        self._btn_rotate.hide()

        self._btn_play = _S("⏸  Pause", bg="#00bfa5", hover="#1de9b6")
        self._btn_play.clicked.connect(self._toggle_play_pause)
        self._btn_play.hide()

        self._btn_delete = _S("Delete", bg="#ef5350", hover="#f44336")
        self._btn_delete.clicked.connect(self._on_delete)

        self._btn_hide = _S("Hide", bg="#ff9800", hover="#ffb74d")
        self._btn_hide.clicked.connect(self._on_hide)

        self._btn_copy = _S("Copy", bg="#43c667", hover="#5ad97f")
        self._btn_copy.clicked.connect(self._on_copy)
        self._btn_copy.hide()

        self._btn_gen_pdf = _S("Generate PDF", bg="#7c5cfc", hover="#9b7dff")
        self._btn_gen_pdf.clicked.connect(self._on_generate_pdf)
        self._btn_gen_pdf.hide()  # shown only in standalone mode

        bar_lay.addStretch()
        for b in (self._btn_select, self._btn_crop, self._btn_rotate, self._btn_play,
                  self._btn_delete, self._btn_hide, self._btn_copy,
                  self._btn_gen_pdf):
            bar_lay.addWidget(b)
        bar_lay.addStretch()

        root.addWidget(bar)

        # --- toast overlay (viewer-local feedback) ---
        self._toast = QLabel(self)
        self._toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast.setFixedHeight(40)
        self._toast.setStyleSheet(
            f"background-color: {COLORS['bg_lighter']}; color: {COLORS['text']}; "
            f"border-radius: 8px; font-size: 13px; font-weight: 600; "
            f"padding: 8px 24px; border: 1px solid {COLORS['border']};"
        )
        self._toast.hide()
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast.hide)

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

    def _ensure_video_widgets(self):
        if self._video_widget and self._media_player and self._audio_output:
            return

        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget

        self._video_widget = QVideoWidget(self._video_page)
        self._video_widget.setStyleSheet("background-color: black;")
        self._video_layout.addWidget(self._video_widget)

        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        self._media_player.setVideoOutput(self._video_widget)
        self._media_player.errorOccurred.connect(self._on_media_error)

    # ────────────────── display ──────────────────

    def _current_path(self) -> str | None:
        if 0 <= self._idx < len(self._items):
            return self._items[self._idx]
        return None

    def _show_current(self):
        if not self._ready:
            return

        self._restore_copy_button()

        # Stop any existing playback
        if self._media_player:
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
        self._btn_rotate.setVisible(not self._is_video)
        self._btn_play.setVisible(self._is_video)
        self._btn_copy.setVisible(not self._is_video)

    def _show_image(self, path: str):
        self._zoom_factor = 1.0
        self._pinch_base_zoom = 1.0
        self._media_stack.setCurrentIndex(0)
        pm = QPixmap(path)
        if pm and not pm.isNull():
            self._current_pixmap = pm
            self._apply_image_zoom(preserve_center=False)
        else:
            self._current_pixmap = None
            self._image_label.setText("Cannot load file")

    def _apply_image_zoom(self, preserve_center: bool = True):
        """Scale the current pixmap relative to the viewport and zoom factor."""
        if not self._current_pixmap:
            return

        viewport = self._image_scroll.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return

        old_size = self._image_label.size()
        hbar = self._image_scroll.horizontalScrollBar()
        vbar = self._image_scroll.verticalScrollBar()

        if preserve_center:
            old_center_x = hbar.value() + viewport.width() / 2
            old_center_y = vbar.value() + viewport.height() / 2
            center_ratio_x = 0.5 if old_size.width() <= viewport.width() else old_center_x / max(1, old_size.width())
            center_ratio_y = 0.5 if old_size.height() <= viewport.height() else old_center_y / max(1, old_size.height())
        else:
            center_ratio_x = 0.5
            center_ratio_y = 0.5

        fit_scale = min(
            viewport.width() / self._current_pixmap.width(),
            viewport.height() / self._current_pixmap.height(),
        )
        fit_scale = max(fit_scale, 0.05)
        target_scale = fit_scale * self._zoom_factor
        target_width = max(1, int(self._current_pixmap.width() * target_scale))
        target_height = max(1, int(self._current_pixmap.height() * target_scale))

        scaled = self._current_pixmap.scaled(
            QSize(target_width, target_height),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._image_label.setPixmap(scaled)
        self._image_label.resize(scaled.size())

        if preserve_center:
            if scaled.width() <= viewport.width():
                hbar.setValue(0)
            else:
                hbar.setValue(int(center_ratio_x * scaled.width() - viewport.width() / 2))
            if scaled.height() <= viewport.height():
                vbar.setValue(0)
            else:
                vbar.setValue(int(center_ratio_y * scaled.height() - viewport.height() / 2))
        else:
            hbar.setValue(max(0, int((scaled.width() - viewport.width()) / 2)))
            vbar.setValue(max(0, int((scaled.height() - viewport.height()) / 2)))

    def _set_zoom_factor(self, zoom: float):
        zoom = max(self._zoom_min, min(self._zoom_max, zoom))
        if abs(zoom - self._zoom_factor) < 0.001:
            return
        self._zoom_factor = zoom
        self._apply_image_zoom(preserve_center=True)

    def _handle_image_zoom_gesture(self, event) -> bool:
        if self._is_video or not self._current_pixmap:
            return False

        if event.type() == QEvent.Type.Wheel:
            if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                return False
            delta = event.angleDelta().y()
            if delta == 0:
                return True
            factor = 1.12 ** (delta / 120.0)
            self._set_zoom_factor(self._zoom_factor * factor)
            event.accept()
            return True

        if event.type() == QEvent.Type.Gesture:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch is None:
                return False
            state = pinch.state()
            if state == Qt.GestureState.GestureStarted:
                self._pinch_base_zoom = self._zoom_factor
            elif state in (Qt.GestureState.GestureUpdated, Qt.GestureState.GestureFinished):
                self._set_zoom_factor(self._pinch_base_zoom * pinch.totalScaleFactor())
            event.accept()
            return True

        return False

    def _show_video(self, path: str):
        self._current_pixmap = None
        self._ensure_video_widgets()
        self._media_stack.setCurrentIndex(1)
        if self._media_player:
            self._media_player.setSource(QUrl.fromLocalFile(path))
            self._media_player.play()
        self._btn_play.setText("⏸  Pause")

    def _toggle_play_pause(self):
        if not self._is_video or not self._media_player:
            return
        from PySide6.QtMultimedia import QMediaPlayer

        state = self._media_player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
            self._btn_play.setText("▶  Play")
        else:
            self._media_player.play()
            self._btn_play.setText("⏸  Pause")

    def _on_media_error(self, error, message):
        """If video playback fails, fall back to a static frame."""
        if not self._media_player:
            return
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

    def _on_rotate(self):
        path = self._current_path()
        if path and not self._is_video:
            self.request_rotate.emit(path)

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

    def _on_copy(self):
        path = self._current_path()
        if not path or self._is_video:
            return
        if copy_files_to_clipboard([path]):
            self._show_copy_feedback()

    def _show_copy_feedback(self):
        self._copy_feedback_active = True
        self._btn_copy.setText("Copied")
        self._copy_feedback_timer.start(5000)

    def show_toast(self, message: str, duration_ms: int = 2500):
        """Show feedback inside the viewer window."""
        self._toast.setText(message)
        self._toast.adjustSize()
        self._toast.setFixedWidth(max(self._toast.sizeHint().width() + 48, 280))
        x = (self.width() - self._toast.width()) // 2
        y = self.height() - 110
        self._toast.move(x, y)
        self._toast.raise_()
        self._toast.show()
        self._toast_timer.start(duration_ms)

    def _restore_copy_button(self):
        if not self._copy_feedback_active:
            return
        self._copy_feedback_timer.stop()
        self._copy_feedback_active = False
        self._btn_copy.setText(self._copy_button_text)

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

    # ────────────────── standalone mode ──────────────────

    def set_standalone_mode(self, standalone: bool):
        """Show/hide controls that are only needed in standalone (file-association) mode."""
        self._btn_gen_pdf.setVisible(standalone)

    def _on_generate_pdf(self):
        self.request_generate_pdf.emit()

    # ────────────────── resize ──────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._ready:
            return
        # Only re-scale images; video widget auto-resizes
        if not self._is_video and self._current_pixmap:
            self._apply_image_zoom(preserve_center=True)
        if self._toast.isVisible():
            x = (self.width() - self._toast.width()) // 2
            y = self.height() - 110
            self._toast.move(x, y)

    def eventFilter(self, watched, event):
        if watched is self._image_scroll.viewport():
            if self._handle_image_zoom_gesture(event):
                return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        if self._media_player:
            self._media_player.stop()
        self.closed.emit()
        super().closeEvent(event)
