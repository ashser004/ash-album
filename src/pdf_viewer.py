"""
Ash Album — PDF Viewer with page selection and PNG export.

Features:
  - Page-by-page viewing with page thumbnails sidebar
  - Zoom in / zoom out (5 % per tap, 1 % per long press)
  - Page indicator (x / y)
  - Select individual pages → convert selected pages to PNG
  - Convert entire PDF to PNG
  - Hide / show toolbar
  - Trackpad (pinch) zoom
  - Up / Down arrows navigate pages; Left / Right navigate PDFs in folder
"""

from __future__ import annotations

import os
from pathlib import Path

import fitz  # PyMuPDF

from PySide6.QtCore import (
    Qt,
    QSize,
    QTimer,
    QRect,
    Signal,
)
from PySide6.QtGui import (
    QFont,
    QImage,
    QKeySequence,
    QPixmap,
    QShortcut,
    QWheelEvent,
    QPainter,
    QPainterPath,
    QColor,
    QBrush,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from .theme import COLORS


# ────────────────── Page thumbnail delegate ──────────────────

PAGE_THUMB_W = 120
PAGE_THUMB_H = 170
PAGE_ITEM_SIZE = QSize(PAGE_THUMB_W, PAGE_THUMB_H + 28)


class _PageThumbDelegate(QStyledItemDelegate):
    """Custom delegate for page thumbnail sidebar."""

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = option.rect
        is_current = bool(index.data(Qt.ItemDataRole.UserRole + 2))
        is_selected_page = bool(index.data(Qt.ItemDataRole.UserRole + 3))

        # Background highlight for current page
        if is_current:
            bg_path = QPainterPath()
            bg_path.addRoundedRect(
                float(rect.x() + 2), float(rect.y() + 2),
                float(rect.width() - 4), float(rect.height() - 4),
                8.0, 8.0,
            )
            painter.fillPath(bg_path, QBrush(QColor("#2a2a50")))
            # Border
            painter.setPen(QPen(QColor(COLORS["accent"]), 2))
            painter.drawRoundedRect(
                rect.x() + 2, rect.y() + 2,
                rect.width() - 4, rect.height() - 4,
                8.0, 8.0,
            )

        # Thumbnail image
        pm = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(pm, QPixmap) and not pm.isNull():
            tx = rect.x() + (rect.width() - pm.width()) // 2
            ty = rect.y() + 6
            painter.drawPixmap(tx, ty, pm)
        
        # Page number
        page_num = index.data(Qt.ItemDataRole.UserRole + 1)
        text_rect = QRect(rect.x(), rect.y() + PAGE_THUMB_H + 2, rect.width(), 22)
        painter.setPen(QColor(COLORS["text_dim"]))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(page_num))

        # Selection badge
        if is_selected_page:
            badge_size = 22
            bx = rect.x() + rect.width() - badge_size - 4
            by = rect.y() + 4
            badge = QPainterPath()
            badge.addRoundedRect(float(bx), float(by), float(badge_size), float(badge_size), 11.0, 11.0)
            painter.fillPath(badge, QBrush(QColor(COLORS["accent"])))
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(QRect(bx, by, badge_size, badge_size), Qt.AlignmentFlag.AlignCenter, "✓")

        painter.restore()

    def sizeHint(self, option, index):
        return PAGE_ITEM_SIZE


# ────────────────── Zoomable page display ──────────────────

class _ZoomablePageLabel(QLabel):
    """QLabel that supports pinch-to-zoom via wheel events."""

    zoom_changed = Signal(float)  # emits new zoom factor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 5.0

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, val):
        self._zoom = max(self._min_zoom, min(self._max_zoom, val))
        self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event: QWheelEvent):
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            step = 0.05 if abs(delta) > 60 else 0.01
            if delta > 0:
                self.zoom = self._zoom + step
            elif delta < 0:
                self.zoom = self._zoom - step
            event.accept()
        else:
            event.ignore()  # let parent scroll


# ────────────────── Main PDF Viewer Dialog ──────────────────

class PDFViewerWindow(QDialog):
    """Full-featured PDF viewer with page selection and PNG export."""

    closed = Signal()

    def __init__(
        self,
        pdf_path: str,
        sibling_pdfs: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._pdf_path = os.path.abspath(pdf_path)
        self._sibling_pdfs = sibling_pdfs or [self._pdf_path]
        self._sibling_idx = 0
        for i, p in enumerate(self._sibling_pdfs):
            if os.path.normcase(os.path.abspath(p)) == os.path.normcase(self._pdf_path):
                self._sibling_idx = i
                break

        self._doc: fitz.Document | None = None
        self._page_count = 0
        self._current_page = 0  # 0-indexed
        self._selected_pages: list[int] = []  # 1-indexed page numbers
        self._zoom = 1.0
        self._toolbar_visible = True
        self._page_pixmaps: dict[int, QPixmap] = {}  # cache rendered pages

        self.setWindowTitle(f"Ash Album — PDF Viewer")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setMinimumSize(1000, 700)

        self._build_ui()
        self._bind_shortcuts()
        self._open_pdf(self._pdf_path)

        self.showMaximized()

    # ════════════════════════════════════════════════════════════
    #  UI Construction
    # ════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──
        self._toolbar = self._make_toolbar()
        root.addWidget(self._toolbar)

        # ── Show toolbar button (visible when toolbar hidden) ──
        self._show_toolbar_btn = QPushButton("▼ Show Tools")
        self._show_toolbar_btn.setFixedHeight(28)
        self._show_toolbar_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_toolbar_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_mid']}; color: {COLORS['text_dim']}; "
            f"border: none; border-bottom: 1px solid {COLORS['border']}; "
            f"font-size: 11px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_light']}; color: {COLORS['text']}; }}"
        )
        self._show_toolbar_btn.clicked.connect(self._toggle_toolbar)
        self._show_toolbar_btn.hide()
        root.addWidget(self._show_toolbar_btn)

        # ── Content area: sidebar + page view ──
        content = QSplitter(Qt.Orientation.Horizontal)
        content.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['border']}; width: 1px; }}"
        )

        # Left sidebar: page thumbnails
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet(f"background-color: {COLORS['bg_mid']};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 4, 0, 0)
        sb_lay.setSpacing(0)

        self._page_list = QListWidget()
        self._page_list.setViewMode(QListWidget.ViewMode.ListMode)
        self._page_list.setIconSize(QSize(PAGE_THUMB_W, PAGE_THUMB_H))
        self._page_list.setSpacing(4)
        self._page_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._page_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._page_list.setStyleSheet(
            f"QListWidget {{ background: {COLORS['bg_mid']}; border: none; outline: none; }}"
            f"QListWidget::item {{ background: transparent; border: none; }}"
        )
        self._page_list.setItemDelegate(_PageThumbDelegate(self._page_list))
        self._page_list.itemClicked.connect(self._on_page_thumb_clicked)
        sb_lay.addWidget(self._page_list, 1)

        content.addWidget(sidebar)

        # Right side: scrollable page view
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll_area.setStyleSheet(
            f"QScrollArea {{ background-color: {COLORS['bg_darkest']}; border: none; }}"
        )

        self._page_label = _ZoomablePageLabel()
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._page_label.setStyleSheet("background-color: transparent;")
        self._page_label.zoom_changed.connect(self._on_trackpad_zoom)
        self._scroll_area.setWidget(self._page_label)

        content.addWidget(self._scroll_area)
        content.setStretchFactor(0, 0)
        content.setStretchFactor(1, 1)

        root.addWidget(content, 1)

        # ── Info bar ──
        self._info_label = QLabel()
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setFixedHeight(26)
        self._info_label.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; "
            f"color: {COLORS['text_dim']}; font-size: 11px;"
        )
        root.addWidget(self._info_label)

        # ── Long-press timers for zoom buttons ──
        self._zoom_in_timer = QTimer(self)
        self._zoom_in_timer.setInterval(100)
        self._zoom_in_timer.timeout.connect(lambda: self._do_zoom(0.01))

        self._zoom_out_timer = QTimer(self)
        self._zoom_out_timer.setInterval(100)
        self._zoom_out_timer.timeout.connect(lambda: self._do_zoom(-0.01))

        self._long_press_delay_in = QTimer(self)
        self._long_press_delay_in.setSingleShot(True)
        self._long_press_delay_in.setInterval(400)
        self._long_press_delay_in.timeout.connect(self._zoom_in_timer.start)

        self._long_press_delay_out = QTimer(self)
        self._long_press_delay_out.setSingleShot(True)
        self._long_press_delay_out.setInterval(400)
        self._long_press_delay_out.timeout.connect(self._zoom_out_timer.start)

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            f"background-color: {COLORS['bg_dark']}; "
            f"border-bottom: 1px solid {COLORS['border']};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        # ── Selected pages label (left side) ──
        self._selected_label = QLabel("")
        self._selected_label.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 11px; font-weight: 600;"
        )
        self._selected_label.setMinimumWidth(100)
        lay.addWidget(self._selected_label)

        lay.addStretch()

        # ── Zoom controls ──
        zoom_label_text = QLabel("Zoom")
        zoom_label_text.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 600;"
        )
        lay.addWidget(zoom_label_text)

        self._btn_zoom_out = self._tool_btn("\u2212")
        self._btn_zoom_out.setFixedWidth(36)
        self._btn_zoom_out.setToolTip("Zoom out (hold for fine control)")
        self._btn_zoom_out.pressed.connect(self._on_zoom_out_pressed)
        self._btn_zoom_out.released.connect(self._on_zoom_out_released)
        lay.addWidget(self._btn_zoom_out)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(52)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 12px; font-weight: 600;"
        )
        lay.addWidget(self._zoom_label)

        self._btn_zoom_in = self._tool_btn("+")
        self._btn_zoom_in.setFixedWidth(36)
        self._btn_zoom_in.setToolTip("Zoom in (hold for fine control)")
        self._btn_zoom_in.pressed.connect(self._on_zoom_in_pressed)
        self._btn_zoom_in.released.connect(self._on_zoom_in_released)
        lay.addWidget(self._btn_zoom_in)

        lay.addSpacing(12)

        # ── Page indicator ──
        self._page_indicator = QLabel("0 / 0")
        self._page_indicator.setFixedWidth(80)
        self._page_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_indicator.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 12px; font-weight: 600;"
        )
        lay.addWidget(self._page_indicator)

        lay.addStretch()

        # ── Action buttons ──
        _S = self._action_btn

        self._btn_select = _S("Select", bg=COLORS["accent"], hover=COLORS["accent_hover"])
        self._btn_select.clicked.connect(self._on_select_page)
        lay.addWidget(self._btn_select)

        self._btn_clear = _S("Clear", bg=COLORS["bg_lighter"], hover=COLORS["bg_light"])
        self._btn_clear.clicked.connect(self._clear_selection)
        lay.addWidget(self._btn_clear)

        self._btn_convert_sel = _S("Convert Page", bg="#43c667", hover="#50d870")
        self._btn_convert_sel.clicked.connect(self._convert_selected_to_png)
        lay.addWidget(self._btn_convert_sel)

        self._btn_convert_all = _S("All → PNG", bg="#3d5afe", hover="#536dfe")
        self._btn_convert_all.clicked.connect(self._convert_all_to_png)
        lay.addWidget(self._btn_convert_all)

        lay.addSpacing(8)

        # ── Hide toolbar button ──
        self._btn_hide_bar = QPushButton("Hide")
        self._btn_hide_bar.setFixedHeight(34)
        self._btn_hide_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_hide_bar.setToolTip("Hide toolbar — view PDF without distractions")
        self._btn_hide_bar.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_lighter']}; color: {COLORS['text']}; "
            f"border: none; border-radius: 8px; padding: 4px 14px; "
            f"font-size: 11px; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent']}; }}"
        )
        self._btn_hide_bar.clicked.connect(self._toggle_toolbar)
        lay.addWidget(self._btn_hide_bar)

        return bar

    @staticmethod
    def _tool_btn(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_lighter']}; color: {COLORS['text']}; "
            f"border: none; border-radius: 8px; padding: 4px 10px; "
            f"font-size: 18px; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent']}; }}"
        )
        return btn

    @staticmethod
    def _action_btn(text: str, bg: str, hover: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(34)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: #ffffff; "
            f"border: none; border-radius: 8px; padding: 4px 14px; "
            f"font-weight: 700; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: {hover}; }}"
            f"QPushButton:pressed {{ opacity: 0.8; }}"
        )
        return btn

    # ════════════════════════════════════════════════════════════
    #  PDF loading
    # ════════════════════════════════════════════════════════════

    def _open_pdf(self, pdf_path: str):
        """Open (or switch to) a PDF file."""
        if self._doc:
            self._doc.close()
            self._doc = None

        self._pdf_path = os.path.abspath(pdf_path)
        self._page_pixmaps.clear()
        self._selected_pages.clear()
        self._current_page = 0

        try:
            self._doc = fitz.open(self._pdf_path)
        except Exception as e:
            self._page_label.setText(f"Cannot open PDF:\n{e}")
            self._page_count = 0
            self._update_ui_state()
            return

        self._page_count = len(self._doc)
        pdf_name = Path(self._pdf_path).stem
        self.setWindowTitle(f"Ash Album — {pdf_name}")

        # Build sidebar thumbnails
        self._build_page_list()

        # Show first page
        self._show_page(0)
        self._update_ui_state()

    def _build_page_list(self):
        """Populate the sidebar with page thumbnails."""
        self._page_list.clear()
        if not self._doc:
            return

        for i in range(self._page_count):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole + 1, i + 1)  # 1-indexed page number
            item.setData(Qt.ItemDataRole.UserRole + 2, i == self._current_page)  # is current
            item.setData(Qt.ItemDataRole.UserRole + 3, False)  # is selected
            item.setSizeHint(PAGE_ITEM_SIZE)

            # Render thumbnail
            pm = self._render_page_thumb(i)
            if pm:
                item.setData(Qt.ItemDataRole.DecorationRole, pm)

            self._page_list.addItem(item)

    def _render_page_thumb(self, page_idx: int) -> QPixmap | None:
        """Render a small thumbnail of a page."""
        if not self._doc or page_idx < 0 or page_idx >= self._page_count:
            return None
        try:
            page = self._doc[page_idx]
            # Scale to fit thumbnail size
            rect = page.rect
            scale = min(PAGE_THUMB_W / rect.width, PAGE_THUMB_H / rect.height) * 0.9
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception:
            return None

    def _render_page_full(self, page_idx: int) -> QPixmap | None:
        """Render a page at the current zoom level for display."""
        if not self._doc or page_idx < 0 or page_idx >= self._page_count:
            return None
        try:
            page = self._doc[page_idx]
            # Base DPI = 150 * zoom factor for good quality
            base_dpi = 150
            scale = (base_dpi / 72.0) * self._zoom
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception:
            return None

    # ════════════════════════════════════════════════════════════
    #  Page display
    # ════════════════════════════════════════════════════════════

    def _show_page(self, page_idx: int):
        """Display the given page (0-indexed)."""
        if page_idx < 0 or page_idx >= self._page_count:
            return

        self._current_page = page_idx

        pm = self._render_page_full(page_idx)
        if pm and not pm.isNull():
            self._page_label.setPixmap(pm)
            # Resize label to pixmap size for scrollability
            self._page_label.setMinimumSize(pm.size())
        else:
            self._page_label.setText("Cannot render page")

        # Update sidebar highlights
        self._update_page_list_highlights()
        self._update_ui_state()

        # Scroll sidebar to current page
        if self._page_list.count() > page_idx:
            self._page_list.scrollToItem(
                self._page_list.item(page_idx),
                QListWidget.ScrollHint.EnsureVisible,
            )

    def _update_page_list_highlights(self):
        """Update current-page and selected-page flags in sidebar."""
        for i in range(self._page_list.count()):
            item = self._page_list.item(i)
            item.setData(Qt.ItemDataRole.UserRole + 2, i == self._current_page)
            item.setData(Qt.ItemDataRole.UserRole + 3, (i + 1) in self._selected_pages)
        self._page_list.viewport().update()

    def _update_ui_state(self):
        """Refresh all dynamic UI elements."""
        # Page indicator
        self._page_indicator.setText(
            f"{self._current_page + 1} / {self._page_count}" if self._page_count else "0 / 0"
        )

        # Zoom label
        self._zoom_label.setText(f"{int(self._zoom * 100)}%")

        # Select button text
        page_1idx = self._current_page + 1
        if page_1idx in self._selected_pages:
            self._btn_select.setText(f"Selected ({page_1idx})")
        else:
            self._btn_select.setText("Select")

        # Convert button text
        if self._selected_pages:
            n = len(self._selected_pages)
            self._btn_convert_sel.setText(f"Selected ({n}) → PNG")
        else:
            self._btn_convert_sel.setText("Page → PNG")

        # Selected label
        if self._selected_pages:
            pages_str = ", ".join(str(p) for p in sorted(self._selected_pages))
            self._selected_label.setText(f"Selected: {pages_str}")
        else:
            self._selected_label.setText("")

        # Info bar
        if self._doc:
            name = Path(self._pdf_path).name
            nice_size = self._nice_size(os.path.getsize(self._pdf_path))
            self._info_label.setText(
                f"{name}   •   {nice_size}   •   {self._page_count} pages   •   "
                f"Page {self._current_page + 1}"
            )
        else:
            self._info_label.setText("")

    # ════════════════════════════════════════════════════════════
    #  Zoom
    # ════════════════════════════════════════════════════════════

    def _do_zoom(self, delta: float):
        """Change zoom by delta and re-render."""
        new_zoom = max(0.10, min(5.0, self._zoom + delta))
        if abs(new_zoom - self._zoom) < 0.001:
            return
        self._zoom = new_zoom
        self._page_label.zoom = self._zoom
        self._show_page(self._current_page)

    def _on_zoom_in_pressed(self):
        self._do_zoom(0.05)
        self._long_press_delay_in.start()

    def _on_zoom_in_released(self):
        self._long_press_delay_in.stop()
        self._zoom_in_timer.stop()

    def _on_zoom_out_pressed(self):
        self._do_zoom(-0.05)
        self._long_press_delay_out.start()

    def _on_zoom_out_released(self):
        self._long_press_delay_out.stop()
        self._zoom_out_timer.stop()

    def _on_trackpad_zoom(self, new_zoom: float):
        """Called when trackpad pinch changes zoom."""
        self._zoom = new_zoom
        self._show_page(self._current_page)

    # ════════════════════════════════════════════════════════════
    #  Toolbar visibility
    # ════════════════════════════════════════════════════════════

    def _toggle_toolbar(self):
        self._toolbar_visible = not self._toolbar_visible
        self._toolbar.setVisible(self._toolbar_visible)
        self._show_toolbar_btn.setVisible(not self._toolbar_visible)

    # ════════════════════════════════════════════════════════════
    #  Page selection
    # ════════════════════════════════════════════════════════════

    def _on_select_page(self):
        page_num = self._current_page + 1  # 1-indexed
        if page_num in self._selected_pages:
            self._selected_pages.remove(page_num)
        else:
            self._selected_pages.append(page_num)
        self._update_page_list_highlights()
        self._update_ui_state()

    def _clear_selection(self):
        self._selected_pages.clear()
        self._update_page_list_highlights()
        self._update_ui_state()

    # ════════════════════════════════════════════════════════════
    #  PNG export
    # ════════════════════════════════════════════════════════════

    def _get_export_folder(self) -> Path | None:
        """Return or create the export folder for the current PDF.
        
        Format: Downloads/<PDFName>folder/
        Only opens a file dialog if the folder does not yet exist.
        """
        pdf_stem = Path(self._pdf_path).stem
        folder_name = f"{pdf_stem}folder"
        downloads = Path.home() / "Downloads"
        target = downloads / folder_name

        if target.exists():
            return target  # Already exists, reuse silently

        # Folder does not exist — let user confirm location
        chosen = QFileDialog.getExistingDirectory(
            self,
            f"Create export folder for '{pdf_stem}'",
            str(downloads),
        )
        if not chosen:
            return None

        # If user picked Downloads, create the subfolder automatically
        chosen_path = Path(chosen)
        if chosen_path == downloads or chosen_path.name != folder_name:
            target = chosen_path / folder_name

        target.mkdir(parents=True, exist_ok=True)
        return target

    def _render_page_hq(self, page_idx: int) -> QImage | None:
        """Render a page at high quality (300 DPI) for PNG export."""
        if not self._doc or page_idx < 0 or page_idx >= self._page_count:
            return None
        try:
            page = self._doc[page_idx]
            dpi = 300
            scale = dpi / 72.0
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            return qimg.copy()
        except Exception:
            return None

    def _convert_selected_to_png(self):
        """Convert selected pages (or current page if none selected) to PNG."""
        pages = sorted(self._selected_pages) if self._selected_pages else [self._current_page + 1]
        folder = self._get_export_folder()
        if not folder:
            return

        self._export_pages_with_progress(pages, folder)

    def _convert_all_to_png(self):
        """Convert all pages of the PDF to PNG."""
        if not self._doc or self._page_count == 0:
            return

        folder = self._get_export_folder()
        if not folder:
            return

        pages = list(range(1, self._page_count + 1))
        self._export_pages_with_progress(pages, folder)

    def _export_pages_with_progress(self, pages: list[int], folder: Path):
        """Export pages to PNG with a progress dialog that shows percentage."""
        total = len(pages)
        pdf_name = Path(self._pdf_path).stem

        progress = QProgressDialog(
            f"Please wait while rendering {pdf_name}... (0%)",
            "Cancel",
            0,
            total,
            self,
        )
        progress.setWindowTitle("Rendering Pages")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setMinimumWidth(420)
        progress.setStyleSheet(
            f"QProgressDialog {{ background-color: {COLORS['bg_mid']}; color: {COLORS['text']}; }}"
            f"QProgressBar {{ background-color: {COLORS['bg_light']}; border: none; "
            f"border-radius: 4px; height: 10px; text-align: center; }}"
            f"QProgressBar::chunk {{ background-color: {COLORS['accent']}; border-radius: 4px; }}"
            f"QLabel {{ color: {COLORS['text']}; font-size: 13px; }}"
            f"QPushButton {{ background-color: {COLORS['danger']}; color: #fff; "
            f"border: none; border-radius: 6px; padding: 6px 20px; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: #f44336; }}"
        )
        progress.show()
        QApplication.processEvents()

        exported = 0
        cancelled = False
        for i, page_num in enumerate(pages):
            if progress.wasCanceled():
                cancelled = True
                break

            pct = int((i / total) * 100)
            progress.setLabelText(
                f"Please wait while rendering {pdf_name}... ({pct}%)\n"
                f"Page {page_num} of {pages[-1]}"
            )
            progress.setValue(i)
            QApplication.processEvents()

            qimg = self._render_page_hq(page_num - 1)
            if qimg:
                out_path = folder / f"{page_num}.png"
                qimg.save(str(out_path), "PNG")
                exported += 1

        progress.setValue(total)
        progress.close()

        if cancelled:
            QMessageBox.information(
                self,
                "Export Cancelled",
                f"Cancelled. {exported} of {total} page(s) were saved to:\n{folder}",
            )
        elif exported:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {exported} page(s) to:\n{folder}",
            )
        else:
            QMessageBox.warning(self, "Export Failed", "No pages could be exported.")

    # ════════════════════════════════════════════════════════════
    #  Navigation
    # ════════════════════════════════════════════════════════════

    def _go_prev_page(self):
        if self._current_page > 0:
            self._show_page(self._current_page - 1)

    def _go_next_page(self):
        if self._current_page < self._page_count - 1:
            self._show_page(self._current_page + 1)

    def _go_prev_pdf(self):
        if len(self._sibling_pdfs) <= 1:
            return
        new_idx = self._sibling_idx - 1
        if new_idx < 0:
            new_idx = len(self._sibling_pdfs) - 1
        self._sibling_idx = new_idx
        self._open_pdf(self._sibling_pdfs[self._sibling_idx])

    def _go_next_pdf(self):
        if len(self._sibling_pdfs) <= 1:
            return
        new_idx = self._sibling_idx + 1
        if new_idx >= len(self._sibling_pdfs):
            new_idx = 0
        self._sibling_idx = new_idx
        self._open_pdf(self._sibling_pdfs[self._sibling_idx])

    def _on_page_thumb_clicked(self, item: QListWidgetItem):
        page_num = item.data(Qt.ItemDataRole.UserRole + 1)
        if page_num:
            self._show_page(page_num - 1)

    # ════════════════════════════════════════════════════════════
    #  Keyboard shortcuts
    # ════════════════════════════════════════════════════════════

    def _bind_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, self._go_prev_page)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, self._go_next_page)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._go_prev_pdf)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._go_next_pdf)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key.Key_Plus), self, lambda: self._do_zoom(0.05))
        QShortcut(QKeySequence(Qt.Key.Key_Minus), self, lambda: self._do_zoom(-0.05))
        QShortcut(QKeySequence("Ctrl+="), self, lambda: self._do_zoom(0.05))
        QShortcut(QKeySequence("Ctrl+-"), self, lambda: self._do_zoom(-0.05))

    # ════════════════════════════════════════════════════════════
    #  Utilities
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _nice_size(b: int) -> str:
        for u in ("B", "KB", "MB", "GB"):
            if b < 1024:
                return f"{b:.1f} {u}" if u != "B" else f"{b} {u}"
            b /= 1024
        return f"{b:.1f} TB"

    # ════════════════════════════════════════════════════════════
    #  Cleanup
    # ════════════════════════════════════════════════════════════

    def closeEvent(self, event):
        if self._doc:
            self._doc.close()
            self._doc = None
        self.closed.emit()
        super().closeEvent(event)
