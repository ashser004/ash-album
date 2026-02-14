"""
Ash Album — Main application window.

Orchestrates the tab bar, sorting, gallery grid, scanner, thumbnail
loader, viewer, crop dialog, PDF export, and bottom selection bar.
Includes dynamic folder discovery — every subfolder found during
scanning automatically appears in the FOLDERS tab sidebar.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPixmap, QImage
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
    VIDEO_EXTENSIONS,
    AppConfig,
)
from .crop_widget import CropDialog
from .gallery_widget import GalleryWidget
from .media_ops import MediaOperations
from .models import MediaItem
from .pdf_export import auto_filename, generate_pdf
from .scanner import ScannerWorker
from .theme import COLORS
from .thumb_loader import ThumbnailWorker
from .viewer_window import ViewerWindow

RECENT_DAYS = 30

# Tab identifiers
TAB_ALL = "ALL"
TAB_PHOTOS = "PHOTOS"
TAB_VIDEOS = "VIDEOS"
TAB_RECENT = "RECENT"
TAB_SCREENSHOTS = "SCREENSHOTS"
TAB_FOLDERS = "FOLDERS"
TAB_HIDDEN = "HIDDEN"
TAB_DELETED = "RECENTLY DELETED"

TAB_ORDER = [TAB_ALL, TAB_PHOTOS, TAB_VIDEOS, TAB_RECENT,
             TAB_SCREENSHOTS, TAB_FOLDERS, TAB_HIDDEN, TAB_DELETED]


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.cfg = config
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(960, 640)

        # ---- data stores ----
        self._all_items: list[MediaItem] = []
        self._selected_paths: set[str] = set()
        self._thumb_cache: dict[str, QPixmap] = {}  # path → QPixmap
        self._current_tab: str = TAB_ALL
        self._current_sort: str = "modified_desc"

        # Folder tracking: folder_path → display_name
        self._discovered_folders: OrderedDict[str, str] = OrderedDict()
        self._active_folder: str | None = None  # for FOLDERS tab

        # ---- workers (created later) ----
        self._scanner: ScannerWorker | None = None
        self._thumb_worker: ThumbnailWorker | None = None

        # ---- active viewer (for confirm_removal callbacks) ----
        self._active_viewer: ViewerWindow | None = None

        # ---- media ops ----
        self._ops = MediaOperations(self.cfg.hidden_dir)

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

        # Page 2: recently deleted list
        self._deleted_list = QListWidget()
        self._deleted_list.setStyleSheet(
            f"QListWidget {{ background: {COLORS['bg_dark']}; border: none; }}"
            f"QListWidget::item {{ padding: 8px 16px; "
            f"border-bottom: 1px solid {COLORS['border']}; }}"
            f"QListWidget::item:hover {{ background: {COLORS['bg_light']}; }}"
        )
        self._stack.addWidget(self._deleted_list)

        # Page 3: FOLDERS tab — splitter with sidebar + gallery
        self._folders_page = self._make_folders_page()
        self._stack.addWidget(self._folders_page)

        # --- bottom bar ---
        root.addWidget(self._make_bottom_bar())

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

        lay.addStretch()

        # Sort combo
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        lay.addWidget(sort_label)

        self._sort_combo = QComboBox()
        for display, key in SORT_OPTIONS:
            self._sort_combo.addItem(display, key)
        # Default to Date Modified (Newest First) → index 4
        self._sort_combo.setCurrentIndex(4)
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        lay.addWidget(self._sort_combo)

        return w

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
        self._sel_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")
        lay.addWidget(self._sel_label)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(30)
        btn_clear.clicked.connect(self._clear_selection)
        lay.addWidget(btn_clear)

        lay.addStretch()

        self._status_label = QLabel("Starting…")
        self._status_label.setObjectName("dimLabel")
        lay.addWidget(self._status_label)

        lay.addStretch()

        btn_pdf = QPushButton("  Generate PDF  ")
        btn_pdf.setObjectName("accentBtn")
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.setFixedHeight(32)
        btn_pdf.clicked.connect(self._generate_pdf)
        lay.addWidget(btn_pdf)

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
        elif tab_id == TAB_DELETED:
            self._stack.setCurrentIndex(2)
            self._refresh_deleted()
        elif tab_id == TAB_FOLDERS:
            self._stack.setCurrentIndex(3)
            self._rebuild_folder_sidebar()
            # If a folder was selected, refresh its gallery
            if self._active_folder:
                self._repopulate_folder_gallery()
        else:
            self._stack.setCurrentIndex(0)
            self._repopulate_gallery()

    # ================================================================
    #  Sorting
    # ================================================================

    def _on_sort_changed(self, idx: int):
        key = self._sort_combo.currentData()
        if key:
            self._current_sort = key
            if self._current_tab == TAB_HIDDEN:
                return
            if self._current_tab == TAB_DELETED:
                return
            if self._current_tab == TAB_FOLDERS:
                self._repopulate_folder_gallery()
                return
            self._repopulate_gallery()

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
            gallery.set_selection(item.path, True)

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
    #  Recently Deleted tab
    # ================================================================

    def _refresh_deleted(self):
        self._deleted_list.clear()
        for entry in reversed(self._ops.get_deleted_this_session()):
            text = f"  {entry['name']}    —    deleted at {entry['time'][:19]}"
            li = QListWidgetItem(text)
            li.setForeground(QColor(COLORS["text_dim"]))
            self._deleted_list.addItem(li)
        if self._deleted_list.count() == 0:
            li = QListWidgetItem("  No files deleted this session.")
            li.setForeground(QColor(COLORS["text_muted"]))
            self._deleted_list.addItem(li)

    # ================================================================
    #  Selection
    # ================================================================

    def _toggle_select(self, path: str):
        if path in self._selected_paths:
            self._selected_paths.discard(path)
        else:
            self._selected_paths.add(path)
        self._gallery.toggle_selection(path)
        self._folder_gallery.toggle_selection(path)
        self._update_sel_label()

    def _clear_selection(self):
        self._selected_paths.clear()
        self._gallery.clear_all_selection()
        self._hidden_gallery.clear_all_selection()
        self._folder_gallery.clear_all_selection()
        self._update_sel_label()

    def _update_sel_label(self):
        n = len(self._selected_paths)
        self._sel_label.setText(f"{n} selected" if n else "0 selected")

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
        dlg.request_add_pdf.connect(self._viewer_add_pdf)
        self._active_viewer = dlg
        dlg.exec()
        self._active_viewer = None

    def _launch_viewer(self, paths: list[str], idx: int):
        dlg = ViewerWindow(paths, idx, self._selected_paths, self)
        dlg.request_select.connect(self._viewer_toggle_select)
        dlg.request_crop.connect(self._do_crop)
        dlg.request_delete.connect(self._do_delete)
        dlg.request_hide.connect(self._do_hide)
        dlg.request_add_pdf.connect(self._viewer_add_pdf)
        self._active_viewer = dlg
        dlg.exec()
        self._active_viewer = None

    def _viewer_toggle_select(self, path: str):
        if path in self._selected_paths:
            self._selected_paths.discard(path)
        else:
            self._selected_paths.add(path)
        # Update galleries if item visible
        if self._gallery.path_exists(path):
            self._gallery.set_selection(path, path in self._selected_paths)
        if self._folder_gallery.path_exists(path):
            self._folder_gallery.set_selection(path, path in self._selected_paths)
        self._update_sel_label()

    def _viewer_add_pdf(self, path: str):
        # Only images
        ext = Path(path).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            return
        self._selected_paths.add(path)
        if self._gallery.path_exists(path):
            self._gallery.set_selection(path, True)
        if self._folder_gallery.path_exists(path):
            self._folder_gallery.set_selection(path, True)
        self._update_sel_label()

    # ================================================================
    #  Actions: delete, hide, unhide, crop
    # ================================================================

    def _do_delete(self, path: str):
        ok = self._ops.delete_to_trash(path)
        if ok:
            self._remove_item(path)
            if self._active_viewer:
                self._active_viewer.confirm_removal(path)

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
        self._selected_paths.discard(path)
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

        default_name = auto_filename()
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF",
            str(Path.home() / "Documents" / default_name),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return
        # If user pressed enter with empty → use auto name
        if not Path(save_path).stem:
            save_path = str(Path(save_path).parent / default_name)

        try:
            generate_pdf(images, save_path)
            QMessageBox.information(
                self, "PDF Created",
                f"Saved {len(images)} image(s) to:\n{save_path}",
            )
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"PDF generation failed:\n{exc}")

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
