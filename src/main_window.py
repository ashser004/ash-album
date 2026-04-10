"""
Ash Album — Main application window.

Orchestrates the tab bar, sorting, gallery grid, scanner, thumbnail
loader, viewer, crop dialog, PDF export, and bottom selection bar.
Includes dynamic folder discovery — every subfolder found during
scanning automatically appears in the FOLDERS tab sidebar.
"""

from __future__ import annotations

import os
import platform
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QPixmap, QImage, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import (
    APP_NAME,
    APP_VERSION,
    IMAGE_EXTENSIONS,
    SCAN_FOLDERS,
    SCREENSHOT_FOLDERS,
    SORT_OPTIONS,
    AppConfig,
)
from .crop_widget import CropDialog
from .default_app import (
    open_default_apps_settings,
    set_default_button_hidden,
    should_show_default_button,
)
from .gallery_widget import GalleryWidget
from .media_ops import MediaOperations, copy_files_to_clipboard
from .models import MediaItem
from .pdf_export import auto_filename, generate_pdf
from .pdf_viewer import PDFViewerWindow
from .scanner import ScannerWorker
from .theme import COLORS
from .update_dialog import UpdateDialog
from .update_manager import (
    DEFAULT_MANIFEST_URL,
    UpdateManifest,
    UpdateCheckWorker,
    cleanup_download_cache,
)
from .thumb_loader import ThumbnailWorker
from .viewer_window import ViewerWindow

RECENT_DAYS = 30
BASE_DIR = Path(__file__).resolve().parents[1]

# Tab identifiers
TAB_ALL = "ALL"
TAB_PHOTOS = "PHOTOS"
TAB_VIDEOS = "VIDEOS"
TAB_RECENT = "RECENT"
TAB_SCREENSHOTS = "SCREENSHOTS"
TAB_FOLDERS = "FOLDERS"
TAB_PDF_PNG = "PDF→PNG"
TAB_HIDDEN = "HIDDEN"

TAB_ORDER = [TAB_ALL, TAB_PHOTOS, TAB_VIDEOS, TAB_RECENT,
             TAB_SCREENSHOTS, TAB_FOLDERS, TAB_PDF_PNG, TAB_HIDDEN]


class _TipPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("infoTipPopup")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(0)

        label = QLabel("Tip: Hold Ctrl and click thumbnails to select multiple files.")
        label.setWordWrap(True)
        label.setFixedWidth(240)
        label.setStyleSheet(f"color: {COLORS['text']}; font-size: 11px;")
        lay.addWidget(label)

        self.setStyleSheet(
            f"QFrame#infoTipPopup {{ background-color: {COLORS['bg_light']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 8px; }}"
        )

    def show_anchored_to(self, anchor: QWidget):
        self.adjustSize()
        pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 8))
        screen = QApplication.screenAt(pos) or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = max(geo.left() + 8, min(pos.x(), geo.right() - self.width() - 8))
            y = pos.y()
            if y + self.height() > geo.bottom() - 8:
                y = anchor.mapToGlobal(QPoint(0, -self.height() - 8)).y()
            y = max(geo.top() + 8, y)
            self.move(x, y)
        else:
            self.move(pos)
        self.show()
        self.raise_()


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.cfg = config
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(960, 640)

        # ---- data stores ----
        self._all_items: list[MediaItem] = []
        self._selected_paths: list[str] = []  # Ordered list to preserve selection order
        self._thumb_cache: dict[str, QPixmap] = {}  # path → QPixmap
        self._current_tab: str = TAB_ALL
        self._current_sort: str = "modified_desc"

        # Folder tracking: folder_path → display_name
        self._discovered_folders: OrderedDict[str, str] = OrderedDict()
        self._active_folder: str | None = None  # for FOLDERS tab

        # PDF→PNG data
        self._pdf_folder_data: dict[str, list[str]] = {}

        # ---- workers (created later) ----
        self._scanner: ScannerWorker | None = None
        self._thumb_worker: ThumbnailWorker | None = None

        # ---- active viewer (for confirm_removal callbacks) ----
        self._active_viewer: ViewerWindow | None = None

        # ---- header help popup ----
        self._info_popup = _TipPopup(self)

        # ---- update state ----
        self._update_worker: UpdateCheckWorker | None = None
        self._update_dialog: UpdateDialog | None = None
        self._update_busy = False
        self._update_cooldown_active = False
        self._update_cooldown_timer = QTimer(self)
        self._update_cooldown_timer.setSingleShot(True)
        self._update_cooldown_timer.timeout.connect(self._finish_update_cooldown)

        # ---- media ops ----
        self._ops = MediaOperations(self.cfg.hidden_dir)

        cleanup_download_cache(Path(self.cfg.base_dir) / "updates")

        # ---- build UI ----
        self._build_ui()
        self._apply_initial_state()

        # ---- start scan ----
        QTimer.singleShot(100, self._start_scan)

    # ================================================================
    #  UI construction
    # ================================================================

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- header ---
        root.addWidget(self._make_header())

        # --- tab bar (scrollable) ---
        root.addWidget(self._make_tab_bar())

        # separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # --- progress bar (scan) ---
        self._progress = QProgressBar()
        self._progress.setFixedHeight(4)
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setTextVisible(False)
        root.addWidget(self._progress)

        # --- stacked content area ---
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        # Page 0: main gallery (ALL / PHOTOS / VIDEOS / RECENT / SCREENSHOTS)
        self._gallery = GalleryWidget()
        self._gallery.item_activated.connect(self._open_viewer)
        self._gallery.item_toggle_select.connect(self._toggle_select)
        self._stack.addWidget(self._gallery)

        # Page 1: hidden gallery
        self._hidden_gallery = GalleryWidget()
        self._hidden_gallery.item_activated.connect(self._open_viewer_hidden)
        self._stack.addWidget(self._hidden_gallery)

        # Page 2: FOLDERS tab — splitter with sidebar + gallery
        self._folders_page = self._make_folders_page()
        self._stack.addWidget(self._folders_page)

        # Page 3: PDF→PNG tab — splitter with folder sidebar + file list
        self._pdf_page = self._make_pdf_page()
        self._stack.addWidget(self._pdf_page)

        # ---- Toast label (overlay) ----
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

        # --- bottom bar ---
        self._bottom_bar = self._make_bottom_bar()
        root.addWidget(self._bottom_bar)

    # ---- header ----

    def _make_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(54)
        w.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(20, 0, 20, 0)

        title = QLabel(APP_NAME.upper())
        title.setObjectName("titleLabel")
        lay.addWidget(title)

        lay.addSpacing(16)

        # "Set as Default" button — hidden when already the default
        self._default_btn = QPushButton("☆  Set as Default")
        self._default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._default_btn.setFixedHeight(30)
        self._default_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['warning']}; color: #111; "
            f"border: none; border-radius: 5px; "
            f"padding: 4px 14px; font-weight: 700; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: #ffc107; }}"
        )
        self._default_btn.clicked.connect(self._on_set_default_clicked)
        lay.addWidget(self._default_btn)

        # Visibility will be set after the window shows
        self._default_btn.setVisible(should_show_default_button(self.cfg))

        lay.addStretch()

        self._info_btn = QPushButton("i")
        self._info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._info_btn.setFixedSize(28, 28)
        self._info_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_light']}; color: {COLORS['text']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 14px; "
            f"padding: 0px; font-weight: 800; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_lighter']}; border-color: {COLORS['accent']}; }}"
        )
        self._info_btn.clicked.connect(self._toggle_info_popup)
        lay.addWidget(self._info_btn)

        lay.addSpacing(8)

        # Refresh button
        btn_refresh = QPushButton("⟳  Refresh")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(32)
        btn_refresh.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_light']}; color: {COLORS['text']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"padding: 4px 16px; font-weight: 600; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent']}; color: #fff; border-color: {COLORS['accent']}; }}"
        )
        btn_refresh.clicked.connect(self._do_refresh)
        lay.addWidget(btn_refresh)

        lay.addSpacing(12)

        # Sort combo
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        lay.addWidget(sort_label)

        self._sort_combo = QComboBox()
        for display, key in SORT_OPTIONS:
            self._sort_combo.addItem(display, key)
        # Default to Date Modified (Newest First) → index 4
        self._sort_combo.setCurrentIndex(4)
        self._sort_combo.setFixedWidth(250)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        lay.addWidget(self._sort_combo)

        lay.addSpacing(6)

        self._update_btn = QPushButton()
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.setFixedSize(30, 30)
        self._update_btn.setToolTip("Check for updates")
        self._update_btn.setIcon(QIcon(str(BASE_DIR / "update.png")))
        self._update_btn.setIconSize(QSize(24, 24))
        self._update_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; padding: 0px; }"
            f"QPushButton:hover {{ background-color: {COLORS['bg_light']}; border-radius: 15px; }}"
            "QPushButton:disabled { background-color: transparent; }"
        )
        self._update_btn.clicked.connect(self._on_update_clicked)
        self._update_btn.setVisible(platform.system() == "Windows")
        lay.addWidget(self._update_btn)

        return w

    def _toggle_info_popup(self):
        if self._info_popup.isVisible():
            self._info_popup.hide()
            return
        self._info_popup.show_anchored_to(self._info_btn)

    def _on_update_clicked(self):
        if platform.system() != "Windows":
            return
        if self._update_busy or not self._update_btn.isEnabled():
            return

        self._show_toast("Checking for updates...", 2000)
        self._update_busy = True
        self._update_cooldown_active = True
        self._update_btn.setEnabled(False)
        self._update_cooldown_timer.start(15000)

        if self._update_worker and self._update_worker.isRunning():
            return

        self._update_worker = UpdateCheckWorker(APP_VERSION, DEFAULT_MANIFEST_URL, self)
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.up_to_date.connect(self._on_update_up_to_date)
        self._update_worker.failed.connect(self._on_update_failed)
        self._update_worker.finished.connect(self._clear_update_worker)
        self._update_worker.start()

    def _clear_update_worker(self):
        self._update_worker = None

    def _finish_update_cooldown(self):
        self._update_cooldown_active = False
        self._restore_update_button()

    def _restore_update_button(self):
        if platform.system() == "Windows" and not self._update_busy and not self._update_cooldown_active:
            self._update_btn.setEnabled(True)

    def _on_update_available(self, manifest: UpdateManifest | object):
        self._update_busy = False
        self._restore_update_button()
        if not isinstance(manifest, UpdateManifest):
            return
        self._update_dialog = UpdateDialog(manifest, Path(self.cfg.base_dir) / "updates", self)
        self._update_dialog.exec()
        self._update_dialog = None

    def _on_update_up_to_date(self):
        self._update_busy = False
        self._restore_update_button()
        self._show_toast("You are already up to date", 2500)

    def _is_no_internet_error(self, message: str) -> bool:
        text = message.lower()
        return any(
            phrase in text
            for phrase in (
                "no internet connection",
                "temporary failure in name resolution",
                "name or service not known",
                "network is unreachable",
                "connection refused",
                "connection reset",
                "no route to host",
                "timed out",
                "failed to establish a new connection",
            )
        )

    def _on_update_failed(self, message: str):
        self._update_busy = False
        self._restore_update_button()
        if self._is_no_internet_error(message):
            self._show_toast("No internet connection", 2500)
            return
        self._show_toast("Could not check for updates", 2500)

    # ---- tab bar ----

    def _make_tab_bar(self) -> QWidget:
        # Use a scroll area so tabs don't overflow
        scroll = QScrollArea()
        scroll.setFixedHeight(48)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {COLORS['bg_darkest']}; border: none; }}"
        )

        inner = QWidget()
        inner.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")
        lay = QHBoxLayout(inner)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(2)

        self._tab_btns: dict[str, QPushButton] = {}
        for tab_id in TAB_ORDER:
            btn = QPushButton(tab_id)
            btn.setObjectName("tabBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(partial(self._on_tab_clicked, tab_id))
            lay.addWidget(btn)
            self._tab_btns[tab_id] = btn

        lay.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ---- folders page ----

    def _make_folders_page(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['border']}; width: 1px; }}"
        )

        # Sidebar: folder list
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background-color: {COLORS['bg_mid']};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 8, 0, 0)
        sb_lay.setSpacing(0)

        sb_title = QLabel("  Folders")
        sb_title.setFixedHeight(36)
        sb_title.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px; "
            f"font-weight: 700; letter-spacing: 0.8px; padding-left: 12px;"
        )
        sb_lay.addWidget(sb_title)

        self._folder_list = QListWidget()
        self._folder_list.setStyleSheet(
            f"QListWidget {{ background: {COLORS['bg_mid']}; border: none; outline: none; }}"
            f"QListWidget::item {{ padding: 10px 16px; color: {COLORS['text']}; "
            f"border-bottom: 1px solid {COLORS['bg_light']}; font-size: 12px; }}"
            f"QListWidget::item:hover {{ background: {COLORS['bg_light']}; }}"
            f"QListWidget::item:selected {{ background: {COLORS['accent']}; color: #fff; }}"
        )
        self._folder_list.currentItemChanged.connect(self._on_folder_selected)
        sb_lay.addWidget(self._folder_list, 1)

        splitter.addWidget(sidebar)

        # Gallery
        self._folder_gallery = GalleryWidget()
        self._folder_gallery.item_activated.connect(self._open_viewer_folder)
        self._folder_gallery.item_toggle_select.connect(self._toggle_select)
        splitter.addWidget(self._folder_gallery)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        return splitter

    # ---- PDF→PNG page ----

    def _make_pdf_page(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {COLORS['border']}; width: 1px; }}"
        )

        # Sidebar: folder list with PDF counts
        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"background-color: {COLORS['bg_mid']};")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 8, 0, 0)
        sb_lay.setSpacing(0)

        sb_title = QLabel("  PDF Folders")
        sb_title.setFixedHeight(36)
        sb_title.setStyleSheet(
            f"color: {COLORS['text_dim']}; font-size: 11px; "
            f"font-weight: 700; letter-spacing: 0.8px; padding-left: 12px;"
        )
        sb_lay.addWidget(sb_title)

        self._pdf_folder_list = QListWidget()
        self._pdf_folder_list.setStyleSheet(
            f"QListWidget {{ background: {COLORS['bg_mid']}; border: none; outline: none; }}"
            f"QListWidget::item {{ padding: 10px 16px; color: {COLORS['text']}; "
            f"border-bottom: 1px solid {COLORS['bg_light']}; font-size: 12px; }}"
            f"QListWidget::item:hover {{ background: {COLORS['bg_light']}; }}"
            f"QListWidget::item:selected {{ background: {COLORS['accent']}; color: #fff; }}"
        )
        self._pdf_folder_list.currentItemChanged.connect(self._on_pdf_folder_selected)
        sb_lay.addWidget(self._pdf_folder_list, 1)

        splitter.addWidget(sidebar)

        # Right side: PDF file list
        right = QWidget()
        right.setStyleSheet(f"background-color: {COLORS['bg_dark']};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(8)

        self._pdf_file_list = QListWidget()
        self._pdf_file_list.setStyleSheet(
            f"QListWidget {{ background: {COLORS['bg_dark']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 8px; outline: none; }}"
            f"QListWidget::item {{ padding: 12px 18px; color: {COLORS['text']}; "
            f"border-bottom: 1px solid {COLORS['bg_light']}; font-size: 13px; }}"
            f"QListWidget::item:hover {{ background: {COLORS['bg_light']}; }}"
            f"QListWidget::item:selected {{ background: {COLORS['accent']}; color: #fff; }}"
        )
        self._pdf_file_list.itemDoubleClicked.connect(self._on_pdf_file_double_clicked)
        right_lay.addWidget(self._pdf_file_list, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        return splitter

    # ---- bottom bar ----

    def _make_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(
            f"background-color: {COLORS['bg_darkest']}; "
            f"border-top: 1px solid {COLORS['border']};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        self._sel_label = QLabel("0 selected")
        self._sel_label.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 13px; font-weight: 700;"
        )
        lay.addWidget(self._sel_label)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(30)
        btn_clear.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_lighter']}; "
            f"color: {COLORS['text']}; border: 1px solid {COLORS['border']}; "
            f"border-radius: 6px; padding: 4px 14px; font-weight: 600; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent']}; color: #fff; border-color: {COLORS['accent']}; }}"
        )
        btn_clear.clicked.connect(self._clear_selection)
        lay.addWidget(btn_clear)

        # Delete Selected button
        self._btn_delete_sel = QPushButton("Delete Selected")
        self._btn_delete_sel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_delete_sel.setFixedHeight(30)
        self._btn_delete_sel.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['danger']}; color: #ffffff; "
            f"border: none; border-radius: 6px; padding: 4px 14px; "
            f"font-weight: 600; font-size: 11px; }}"
            f"QPushButton:hover {{ background-color: #f44336; }}"
        )
        self._btn_delete_sel.clicked.connect(self._delete_selected)
        lay.addWidget(self._btn_delete_sel)

        lay.addStretch()

        self._status_label = QLabel("Starting…")
        self._status_label.setObjectName("dimLabel")
        lay.addWidget(self._status_label)

        lay.addStretch()

        self._btn_copy_sel = QPushButton("Copy")
        self._btn_copy_sel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copy_sel.setFixedHeight(34)
        self._btn_copy_sel.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['success']}; color: #ffffff; "
            f"border: none; border-radius: 7px; padding: 6px 18px; "
            f"font-weight: 700; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: #5fd07b; }}"
        )
        self._btn_copy_sel.clicked.connect(self._copy_selected_images)
        self._btn_copy_sel.setVisible(False)
        lay.addWidget(self._btn_copy_sel)

        self._btn_gen_pdf = QPushButton("  Generate PDF  ")
        self._btn_gen_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_gen_pdf.setFixedHeight(34)
        self._btn_gen_pdf.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent']}; color: #ffffff; "
            f"border: none; border-radius: 7px; padding: 6px 24px; "
            f"font-weight: 700; font-size: 13px; letter-spacing: 0.4px; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}"
        )
        self._btn_gen_pdf.clicked.connect(self._generate_pdf)
        lay.addWidget(self._btn_gen_pdf)

        self._update_sel_label()

        return bar

    # ---- initial state ----

    def _apply_initial_state(self):
        self._tab_btns[TAB_ALL].setChecked(True)
        self._progress.hide()

    # ================================================================
    #  Scanner
    # ================================================================

    def _start_scan(self):
        self._progress.show()
        self._status_label.setText("Scanning…")

        self._scanner = ScannerWorker(
            scan_folders=list(SCAN_FOLDERS),
            hidden_dir=self.cfg.hidden_dir,
        )
        self._scanner.items_found.connect(self._on_items_found)
        self._scanner.scan_progress.connect(self._on_scan_progress)
        self._scanner.scan_finished.connect(self._on_scan_finished)
        self._scanner.start()

    def _on_items_found(self, batch: list[MediaItem]):
        self._all_items.extend(batch)

        # Track folders
        for item in batch:
            fp = item.folder_path
            if fp not in self._discovered_folders:
                self._discovered_folders[fp] = item.folder

        # If the current tab matches, add to gallery immediately
        for item in batch:
            if self._item_matches_tab(item, self._current_tab):
                self._gallery.add_media_item(item.name, item.path, item.media_type)

        # Queue thumbnails
        if self._thumb_worker is None:
            self._thumb_worker = ThumbnailWorker(self.cfg.cache_dir)
            self._thumb_worker.thumbnail_ready.connect(self._on_thumb_ready)
            self._thumb_worker.start()
        self._thumb_worker.enqueue_batch([i.path for i in batch])

    def _on_scan_progress(self, text: str):
        self._status_label.setText(text)

    def _on_scan_finished(self, total: int):
        self._progress.hide()
        self._status_label.setText(f"{total} files found  •  {len(self._discovered_folders)} folders")

        # Determine whether the screenshots tab should be visible
        has_screenshots = any(
            any(
                item.folder_path.lower().rstrip("\\/ ") == str(sf).lower().rstrip("\\/ ")
                for sf in SCREENSHOT_FOLDERS
            )
            for item in self._all_items
        )
        if has_screenshots:
            self._tab_btns[TAB_SCREENSHOTS].show()
        else:
            self._tab_btns[TAB_SCREENSHOTS].hide()

        # Rebuild folder sidebar
        self._rebuild_folder_sidebar()

        # Re-sort current view
        self._repopulate_gallery()

    def _on_thumb_ready(self, path: str, qimg: QImage):
        pm = QPixmap.fromImage(qimg)
        self._thumb_cache[path] = pm
        # Update whichever gallery is visible
        self._gallery.set_thumbnail_pixmap(path, pm)
        self._hidden_gallery.set_thumbnail_pixmap(path, pm)
        self._folder_gallery.set_thumbnail_pixmap(path, pm)

    # ================================================================
    #  Folder sidebar
    # ================================================================

    def _rebuild_folder_sidebar(self):
        """Populate the FOLDERS-tab sidebar with every discovered folder,
        sorted alphabetically, with item counts."""
        self._folder_list.clear()

        # Count files per folder
        counts: dict[str, int] = {}
        for item in self._all_items:
            counts[item.folder_path] = counts.get(item.folder_path, 0) + 1

        # Sort folders alphabetically by display name
        sorted_folders = sorted(
            self._discovered_folders.items(),
            key=lambda kv: kv[1].lower(),
        )
        for folder_path, display_name in sorted_folders:
            cnt = counts.get(folder_path, 0)
            li = QListWidgetItem(f"{display_name}  ({cnt})")
            li.setData(Qt.ItemDataRole.UserRole, folder_path)
            self._folder_list.addItem(li)

    def _on_folder_selected(self, current: QListWidgetItem | None, prev=None):
        if current is None:
            return
        folder_path = current.data(Qt.ItemDataRole.UserRole)
        self._active_folder = folder_path
        self._repopulate_folder_gallery()

    def _repopulate_folder_gallery(self):
        if not self._active_folder:
            return
        filtered = [
            i for i in self._all_items
            if i.folder_path == self._active_folder
        ]
        filtered = self._sort_items(filtered, self._current_sort)

        self._folder_gallery.clear_gallery()

        use_date_groups = self._current_sort in (
            "created_desc", "created_asc", "modified_desc", "modified_asc",
        )

        if use_date_groups:
            groups = self._group_by_date(filtered, self._current_sort)
            for date_str, items in groups:
                self._folder_gallery.add_date_header(date_str)
                for item in items:
                    self._add_gallery_item(self._folder_gallery, item)
        else:
            for item in filtered:
                self._add_gallery_item(self._folder_gallery, item)

    # ================================================================
    #  Tab switching
    # ================================================================

    def _on_tab_clicked(self, tab_id: str):
        # Uncheck others
        for tid, btn in self._tab_btns.items():
            btn.setChecked(tid == tab_id)
        self._current_tab = tab_id

        if tab_id == TAB_HIDDEN:
            self._stack.setCurrentIndex(1)
            self._refresh_hidden()
        elif tab_id == TAB_FOLDERS:
            self._stack.setCurrentIndex(2)
            self._rebuild_folder_sidebar()
            # If a folder was selected, refresh its gallery
            if self._active_folder:
                self._repopulate_folder_gallery()
        elif tab_id == TAB_PDF_PNG:
            self._stack.setCurrentIndex(3)
            self._scan_pdf_folders()
        else:
            self._stack.setCurrentIndex(0)
            self._repopulate_gallery()

        # Hide bottom bar on PDF→PNG tab, show on all others
        self._bottom_bar.setVisible(tab_id != TAB_PDF_PNG)

    # ================================================================
    #  Sorting
    # ================================================================

    def _on_sort_changed(self, idx: int):
        key = self._sort_combo.currentData()
        if key:
            self._current_sort = key
            if self._current_tab == TAB_HIDDEN:
                return
            if self._current_tab == TAB_FOLDERS:
                self._repopulate_folder_gallery()
                return
            if self._current_tab == TAB_PDF_PNG:
                return  # no sorting for PDF tab
            self._repopulate_gallery()

    # ================================================================
    #  PDF→PNG tab
    # ================================================================

    def _scan_pdf_folders(self):
        """Scan known folders for PDFs and populate the PDF folder sidebar."""
        self._pdf_folder_list.clear()

        from .config import SCAN_FOLDERS

        pdf_folders: dict[str, list[str]] = {}  # folder_path → [pdf paths]
        visited_dirs: set[str] = set()

        for scan_root in SCAN_FOLDERS:
            scan_root = Path(scan_root)
            if not scan_root.exists():
                continue
            for root, dirs, files in os.walk(scan_root, topdown=True):
                # Skip hidden/system directories
                dirs[:] = [
                    d for d in dirs
                    if d not in {"$RECYCLE.BIN", "System Volume Information",
                                 "AppData", ".git", "__pycache__",
                                 "node_modules", ".venv", "venv"}
                    and not d.startswith(".")
                ]
                root_path = Path(root)
                try:
                    resolved = str(root_path.resolve()).lower()
                except OSError:
                    continue
                if resolved in visited_dirs:
                    continue
                visited_dirs.add(resolved)

                pdfs_in_dir = []
                for fname in files:
                    if fname.lower().endswith(".pdf"):
                        pdfs_in_dir.append(str(root_path / fname))

                if pdfs_in_dir:
                    folder_key = str(root_path)
                    if folder_key not in pdf_folders:
                        pdf_folders[folder_key] = []
                    pdf_folders[folder_key].extend(pdfs_in_dir)

        # Populate sidebar sorted by folder name
        self._pdf_folder_data = pdf_folders
        sorted_folders = sorted(pdf_folders.keys(), key=lambda p: Path(p).name.lower())
        for folder_path in sorted_folders:
            count = len(pdf_folders[folder_path])
            display = f"{Path(folder_path).name}  ({count})"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, folder_path)
            self._pdf_folder_list.addItem(item)

    def _on_pdf_folder_selected(self, current: QListWidgetItem | None, prev=None):
        if current is None:
            return
        folder_path = current.data(Qt.ItemDataRole.UserRole)
        self._pdf_file_list.clear()

        pdfs = self._pdf_folder_data.get(folder_path, [])
        pdfs.sort(key=lambda p: Path(p).name.lower())
        for pdf_path in pdfs:
            name = Path(pdf_path).name
            item = QListWidgetItem(f"📄  {name}")
            item.setData(Qt.ItemDataRole.UserRole, pdf_path)
            self._pdf_file_list.addItem(item)

    def _on_pdf_file_double_clicked(self, item: QListWidgetItem):
        pdf_path = item.data(Qt.ItemDataRole.UserRole)
        if not pdf_path:
            return
        # Gather sibling PDFs from the same folder
        folder = str(Path(pdf_path).parent)
        siblings = self._pdf_folder_data.get(folder, [pdf_path])
        siblings = sorted(siblings, key=lambda p: Path(p).name.lower())
        self._open_pdf_viewer(pdf_path, siblings)

    def _open_pdf_viewer(self, pdf_path: str, sibling_pdfs: list[str] | None = None):
        """Open the PDF viewer dialog."""
        dlg = PDFViewerWindow(pdf_path, sibling_pdfs, self)
        dlg.exec()

    # ================================================================
    #  Gallery population
    # ================================================================

    def _repopulate_gallery(self):
        """Clear and repopulate the main gallery for the current tab + sort."""
        filtered = [i for i in self._all_items
                    if self._item_matches_tab(i, self._current_tab)]
        filtered = self._sort_items(filtered, self._current_sort)

        self._gallery.clear_gallery()

        # Insert date section headers when sorting by date
        use_date_groups = self._current_sort in (
            "created_desc", "created_asc", "modified_desc", "modified_asc",
        )

        if use_date_groups:
            groups = self._group_by_date(filtered, self._current_sort)
            for date_str, items in groups:
                self._gallery.add_date_header(date_str)
                for item in items:
                    self._add_gallery_item(self._gallery, item)
        else:
            for item in filtered:
                self._add_gallery_item(self._gallery, item)

    def _add_gallery_item(self, gallery, item: MediaItem):
        """Helper: add a single media item to a gallery with thumb + selection."""
        gallery.add_media_item(item.name, item.path, item.media_type)
        pm = self._thumb_cache.get(item.path)
        if pm:
            gallery.set_thumbnail_pixmap(item.path, pm)
        if item.path in self._selected_paths:
            order = self._selected_paths.index(item.path) + 1
            gallery.set_selection(item.path, True, order)

    @staticmethod
    def _group_by_date(
        items: list[MediaItem], sort_key: str
    ) -> list[tuple[str, list[MediaItem]]]:
        """Group already-sorted items by date. Returns (date_label, items) pairs."""
        if sort_key in ("created_desc", "created_asc"):
            ts_fn = lambda i: i.created
        else:
            ts_fn = lambda i: i.modified

        groups: list[tuple[str, list[MediaItem]]] = []
        prev_label = ""
        for item in items:
            label = datetime.fromtimestamp(ts_fn(item)).strftime("%d %B %Y")
            if label != prev_label:
                groups.append((label, []))
                prev_label = label
            groups[-1][1].append(item)
        return groups

    def _item_matches_tab(self, item: MediaItem, tab: str) -> bool:
        if tab == TAB_ALL:
            return True
        if tab == TAB_PHOTOS:
            return item.media_type == "photo"
        if tab == TAB_VIDEOS:
            return item.media_type == "video"
        if tab == TAB_RECENT:
            cutoff = (datetime.now() - timedelta(days=RECENT_DAYS)).timestamp()
            return item.modified >= cutoff
        if tab == TAB_SCREENSHOTS:
            for sf in SCREENSHOT_FOLDERS:
                try:
                    Path(item.path).relative_to(sf)
                    return item.media_type == "photo"
                except ValueError:
                    continue
            return False
        return False

    @staticmethod
    def _sort_items(items: list[MediaItem], key: str) -> list[MediaItem]:
        if key == "name_asc":
            return sorted(items, key=lambda i: i.name.lower())
        if key == "name_desc":
            return sorted(items, key=lambda i: i.name.lower(), reverse=True)
        if key == "created_desc":
            return sorted(items, key=lambda i: i.created, reverse=True)
        if key == "created_asc":
            return sorted(items, key=lambda i: i.created)
        if key == "modified_desc":
            return sorted(items, key=lambda i: i.modified, reverse=True)
        if key == "modified_asc":
            return sorted(items, key=lambda i: i.modified)
        if key == "size_asc":
            return sorted(items, key=lambda i: i.size)
        if key == "size_desc":
            return sorted(items, key=lambda i: i.size, reverse=True)
        return items

    # ================================================================
    #  Hidden tab
    # ================================================================

    def _refresh_hidden(self):
        self._hidden_gallery.clear_gallery()
        for fpath in self._ops.get_hidden_files():
            item = MediaItem.from_path(fpath)
            if item:
                self._hidden_gallery.add_media_item(item.name, item.path, item.media_type)
                pm = self._thumb_cache.get(item.path)
                if pm:
                    self._hidden_gallery.set_thumbnail_pixmap(item.path, pm)
                # Queue thumb generation if needed
                if not pm and self._thumb_worker:
                    self._thumb_worker.enqueue(item.path)

    # ================================================================
    #  Toast notifications
    # ================================================================

    def _show_toast(self, message: str, duration_ms: int = 3000):
        self._toast.setText(message)
        self._toast.adjustSize()
        self._toast.setFixedWidth(max(self._toast.sizeHint().width() + 48, 280))
        # Position at bottom-center, above the bottom bar
        x = (self.width() - self._toast.width()) // 2
        y = self.height() - 110
        self._toast.move(x, y)
        self._toast.raise_()
        self._toast.show()
        self._toast_timer.start(duration_ms)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Reposition toast if visible
        if self._toast.isVisible():
            x = (self.width() - self._toast.width()) // 2
            y = self.height() - 110
            self._toast.move(x, y)

    # ================================================================
    #  Selection
    # ================================================================

    def _toggle_select(self, path: str):
        if path in self._selected_paths:
            self._selected_paths.remove(path)
            # Update order numbers for all remaining selections
            self._update_all_selection_orders()
        else:
            self._selected_paths.append(path)
            order = len(self._selected_paths)
            self._gallery.set_selection(path, True, order)
            self._folder_gallery.set_selection(path, True, order)
        self._update_sel_label()

    def _update_all_selection_orders(self):
        """Update selection order on all galleries after reordering."""
        self._gallery.update_all_selection_orders(self._selected_paths)
        self._folder_gallery.update_all_selection_orders(self._selected_paths)
        self._hidden_gallery.update_all_selection_orders(self._selected_paths)

    def _clear_selection(self):
        self._selected_paths.clear()
        self._gallery.clear_all_selection()
        self._hidden_gallery.clear_all_selection()
        self._folder_gallery.clear_all_selection()
        self._update_sel_label()

    def _update_sel_label(self):
        n = len(self._selected_paths)
        self._sel_label.setText(f"{n} selected" if n else "0 selected")
        if hasattr(self, "_btn_copy_sel"):
            self._btn_copy_sel.setVisible(bool(self._selected_images_for_copy()))

    def _selected_images_for_copy(self) -> list[str]:
        images: list[str] = []
        for path in self._selected_paths:
            candidate = Path(path)
            if candidate.suffix.lower() not in IMAGE_EXTENSIONS or not candidate.exists():
                return []
            images.append(str(candidate))
        return images

    def _copy_selected_images(self):
        images = self._selected_images_for_copy()
        if not images:
            self._show_toast("No copyable images selected")
            return
        if copy_files_to_clipboard(images):
            self._show_toast(f"Copied {len(images)} image(s) to clipboard")
        else:
            self._show_toast("Could not copy selected files")

    # ================================================================
    #  Viewer
    # ================================================================

    def _open_viewer(self, path: str):
        paths = self._gallery.get_all_paths()
        idx = paths.index(path) if path in paths else 0
        self._launch_viewer(paths, idx)

    def _open_viewer_folder(self, path: str):
        paths = self._folder_gallery.get_all_paths()
        idx = paths.index(path) if path in paths else 0
        self._launch_viewer(paths, idx)

    def _open_viewer_hidden(self, path: str):
        paths = self._hidden_gallery.get_all_paths()
        idx = paths.index(path) if path in paths else 0
        dlg = ViewerWindow(paths, idx, self._selected_paths, self)
        # For hidden viewer, swap hide → unhide behaviour
        dlg._btn_hide.setText("Unhide")
        dlg.request_hide.connect(self._do_unhide)
        dlg.request_select.connect(self._viewer_toggle_select)
        dlg.request_crop.connect(self._do_crop)
        dlg.request_delete.connect(self._do_delete)
        self._active_viewer = dlg
        dlg.exec()
        self._active_viewer = None

    def _launch_viewer(self, paths: list[str], idx: int):
        dlg = ViewerWindow(paths, idx, self._selected_paths, self)
        dlg.request_select.connect(self._viewer_toggle_select)
        dlg.request_crop.connect(self._do_crop)
        dlg.request_delete.connect(self._do_delete)
        dlg.request_hide.connect(self._do_hide)
        self._active_viewer = dlg
        dlg.exec()
        self._active_viewer = None

    def _viewer_toggle_select(self, path: str):
        if path in self._selected_paths:
            self._selected_paths.remove(path)
            # Update order numbers for all remaining selections
            self._update_all_selection_orders()
        else:
            self._selected_paths.append(path)
            order = len(self._selected_paths)
            # Update galleries if item visible
            if self._gallery.path_exists(path):
                self._gallery.set_selection(path, True, order)
            if self._folder_gallery.path_exists(path):
                self._folder_gallery.set_selection(path, True, order)
        self._update_sel_label()

    # ================================================================
    #  Actions: delete, hide, unhide, crop
    # ================================================================

    def _do_delete(self, path: str):
        ok = self._ops.delete_to_trash(path)
        if ok:
            name = Path(path).name
            self._remove_item(path)
            if self._active_viewer:
                self._active_viewer.confirm_removal(path)
            self._show_toast(f"🗑  {name}  moved to Recycle Bin")

    def _do_hide(self, path: str):
        new_path = self._ops.hide_file(path)
        if new_path:
            self._remove_item(path)
            if self._active_viewer:
                self._active_viewer.confirm_removal(path)

    def _do_unhide(self, path: str):
        restored = self._ops.unhide_file(path)
        if restored:
            self._hidden_gallery.remove_by_path(path)
            if self._active_viewer:
                self._active_viewer.confirm_removal(path)
            # Re-add to main items
            item = MediaItem.from_path(restored)
            if item:
                self._all_items.append(item)
                if item.folder_path not in self._discovered_folders:
                    self._discovered_folders[item.folder_path] = item.folder
            # Invalidate thumb cache for old path
            self._thumb_cache.pop(path, None)
            if item and self._thumb_worker:
                self._thumb_worker.enqueue(item.path)

    def _remove_item(self, path: str):
        """Remove an item from all data structures."""
        self._all_items = [i for i in self._all_items if i.path != path]
        if path in self._selected_paths:
            self._selected_paths.remove(path)
            # Update all galleries with new order numbers
            self._update_all_selection_orders()
        self._gallery.remove_by_path(path)
        self._hidden_gallery.remove_by_path(path)
        self._folder_gallery.remove_by_path(path)
        self._thumb_cache.pop(path, None)
        self._update_sel_label()

    def _do_crop(self, path: str):
        dlg = CropDialog(path, self)
        dlg.cropped.connect(self._on_cropped)
        dlg.exec()

    def _on_cropped(self, saved_path: str):
        # Invalidate cached thumbnail so it regenerates
        self._thumb_cache.pop(saved_path, None)
        if self._thumb_worker:
            self._thumb_worker.invalidate(saved_path)
            self._thumb_worker.enqueue(saved_path)
        # If it's a new file, add to items
        existing = {i.path for i in self._all_items}
        if saved_path not in existing:
            item = MediaItem.from_path(saved_path)
            if item:
                self._all_items.append(item)
                if item.folder_path not in self._discovered_folders:
                    self._discovered_folders[item.folder_path] = item.folder
                if self._item_matches_tab(item, self._current_tab):
                    self._gallery.add_media_item(item.name, item.path, item.media_type)

    # ================================================================
    #  PDF generation
    # ================================================================

    def _generate_pdf(self):
        # Only images from selection
        img_exts = IMAGE_EXTENSIONS
        images = [
            p for p in self._selected_paths
            if Path(p).suffix.lower() in img_exts and Path(p).exists()
        ]
        if not images:
            QMessageBox.information(
                self, "No Images",
                "Select at least one image to generate a PDF.\n\n"
                "Tip: Ctrl-click thumbnails or use the Select button in the viewer.",
            )
            return

        # Ask page size
        page_mode = self._ask_pdf_page_size()
        if not page_mode:
            return

        default_name = auto_filename()
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF",
            str(Path.home() / "Downloads" / default_name),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return
        # If user pressed enter with empty → use auto name
        if not Path(save_path).stem:
            save_path = str(Path(save_path).parent / default_name)

        try:
            total = len(images)
            cancelled = False

            progress = QProgressDialog(
                f"Generating PDF... (0/{total})",
                "Cancel",
                0, total, self,
            )
            progress.setWindowTitle("Generating PDF")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setMinimumWidth(400)
            progress.setStyleSheet(
                f"QProgressDialog {{ background-color: {COLORS['bg_mid']}; color: {COLORS['text']}; "
                f"min-height: 160px; padding: 14px; }}"
                f"QProgressBar {{ background-color: {COLORS['bg_light']}; border: none; "
                f"border-radius: 6px; min-height: 22px; max-height: 22px; text-align: center; "
                f"font-size: 12px; font-weight: 600; color: {COLORS['text']}; "
                f"margin-bottom: 14px; }}"
                f"QProgressBar::chunk {{ background-color: {COLORS['accent']}; border-radius: 6px; }}"
                f"QLabel {{ color: {COLORS['text']}; font-size: 13px; margin-bottom: 8px; }}"
                f"QPushButton {{ background-color: {COLORS['danger']}; color: #fff; "
                f"border: none; border-radius: 6px; padding: 6px 20px; "
                f"font-weight: 700; margin-top: 6px; }}"
                f"QPushButton:hover {{ background-color: #f44336; }}"
            )
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
                self._show_toast("PDF generation cancelled")
            else:
                QMessageBox.information(
                    self, "PDF Created",
                    f"Saved {len(images)} image(s) to:\n{save_path}",
                )
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"PDF generation failed:\n{exc}")

    def _ask_pdf_page_size(self) -> str | None:
        """Show dialog to choose PDF page size. Returns 'a4', 'default', or None."""
        msg = QMessageBox(self)
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

    # ================================================================
    #  Bulk delete selected
    # ================================================================

    def _delete_selected(self):
        paths = list(self._selected_paths)
        if not paths:
            self._show_toast("No items selected")
            return
        count = len(paths)
        reply = QMessageBox.question(
            self, "Delete Selected",
            f"Move {count} selected item(s) to the Recycle Bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        deleted = 0
        for p in paths:
            if self._ops.delete_to_trash(p):
                self._remove_item(p)
                deleted += 1
        self._show_toast(f"🗑  {deleted} item(s) moved to Recycle Bin")

    # ================================================================
    #  Refresh / rescan
    # ================================================================

    def _do_refresh(self):
        """Stop current workers, clear data, and rescan everything."""
        # Stop workers
        if self._scanner:
            self._scanner.stop()
            self._scanner.wait(2000)
            self._scanner = None
        if self._thumb_worker:
            self._thumb_worker.stop()
            self._thumb_worker.wait(2000)
            self._thumb_worker = None

        # Clear data stores
        self._all_items.clear()
        self._selected_paths.clear()
        self._thumb_cache.clear()
        self._discovered_folders.clear()
        self._active_folder = None

        # Clear galleries
        self._gallery.clear_gallery()
        self._hidden_gallery.clear_gallery()
        self._folder_gallery.clear_gallery()
        self._folder_list.clear()

        self._update_sel_label()
        self._show_toast("⟳  Refreshing…", 1500)

        # Restart scan
        QTimer.singleShot(200, self._start_scan)

    # ================================================================
    #  Set as Default handler
    # ================================================================

    def _on_set_default_clicked(self):
        """Open OS default-app settings, then re-check after a delay."""
        set_default_button_hidden(True, self.cfg)
        self.cfg.default_app_asked = True
        self.cfg.save()
        self._default_btn.hide()

        opened = open_default_apps_settings()
        if opened:
            self._show_toast("Opening Default Apps settings…", 2500)
        else:
            self._show_toast("Could not open settings", 2000)

    def _refresh_default_btn(self):
        """Show / hide the 'Set as Default' button based on current state."""
        self._default_btn.setVisible(should_show_default_button(self.cfg))

    # ================================================================
    #  Cleanup
    # ================================================================

    def closeEvent(self, event):
        if self._scanner:
            self._scanner.stop()
            self._scanner.wait(2000)
        if self._thumb_worker:
            self._thumb_worker.stop()
            self._thumb_worker.wait(2000)
        super().closeEvent(event)
