"""
Ash Album — Gallery grid widget.

Uses QListWidget in IconMode with a custom delegate for a polished
thumbnail grid with rounded corners, video badges, and selection
checkmarks.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRect, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
)

from .config import THUMB_SIZE

ITEM_W = 200
ITEM_H = 230
ITEM_SIZE = QSize(ITEM_W, ITEM_H)

# Custom data roles
ROLE_PATH = Qt.ItemDataRole.UserRole + 1
ROLE_MEDIA_TYPE = Qt.ItemDataRole.UserRole + 2
ROLE_LOADED = Qt.ItemDataRole.UserRole + 3
ROLE_APP_SELECTED = Qt.ItemDataRole.UserRole + 4
ROLE_DATE_HEADER = Qt.ItemDataRole.UserRole + 5

DATE_HEADER_H = 44


# ────────────────────────────────────────────────────────────────
#  Delegate
# ────────────────────────────────────────────────────────────────

class ThumbnailDelegate(QStyledItemDelegate):
    """Custom painting for gallery thumbnails."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._placeholder = self._make_placeholder()

    @staticmethod
    def _make_placeholder() -> QPixmap:
        pm = QPixmap(THUMB_SIZE, THUMB_SIZE)
        pm.fill(QColor("#1c1c2e"))
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        # Subtle icon
        p.setBrush(QBrush(QColor("#2a2a44")))
        p.drawRoundedRect(40, 40, 100, 100, 16, 16)
        p.setPen(QColor("#3d3d5c"))
        p.setFont(QFont("Segoe UI", 28))
        p.drawText(QRect(40, 40, 100, 100), Qt.AlignmentFlag.AlignCenter, "🖼")
        p.end()
        return pm

    # ---- painting ----

    def paint(self, painter: QPainter, option, index):
        # ── Date header item ──
        if index.data(ROLE_DATE_HEADER):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect: QRect = option.rect
            # Separator line
            painter.setPen(QPen(QColor("#2a2a3e"), 1))
            painter.drawLine(rect.x() + 16, rect.bottom() - 1,
                             rect.right() - 16, rect.bottom() - 1)
            # Date text
            painter.setPen(QColor("#8686a4"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            painter.drawText(
                QRect(rect.x() + 16, rect.y(), rect.width() - 32, rect.height() - 4),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                index.data(Qt.ItemDataRole.DisplayRole) or "",
            )
            painter.restore()
            return

        # ── Normal thumbnail item ──
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect: QRect = option.rect
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        app_sel = bool(index.data(ROLE_APP_SELECTED))
        media_type: str = index.data(ROLE_MEDIA_TYPE) or ""

        # --- card background on hover / selection ---
        if hovered or app_sel:
            bg = QColor("#262640") if hovered else QColor("#1e1e36")
            card = QPainterPath()
            card.addRoundedRect(
                float(rect.x() + 3), float(rect.y() + 3),
                float(rect.width() - 6), float(rect.height() - 6),
                10.0, 10.0,
            )
            painter.fillPath(card, QBrush(bg))

        # --- thumbnail area ---
        tx = rect.x() + (rect.width() - THUMB_SIZE) // 2
        ty = rect.y() + 10
        thumb_rect = QRect(tx, ty, THUMB_SIZE, THUMB_SIZE)

        # Get pixmap
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if isinstance(icon, QIcon) and not icon.isNull():
            pm = icon.pixmap(THUMB_SIZE, THUMB_SIZE)
        else:
            pm = self._placeholder

        if not pm.isNull():
            scaled = pm.scaled(
                THUMB_SIZE, THUMB_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            dx = tx + (THUMB_SIZE - scaled.width()) // 2
            dy = ty + (THUMB_SIZE - scaled.height()) // 2

            clip = QPainterPath()
            clip.addRoundedRect(
                float(dx), float(dy),
                float(scaled.width()), float(scaled.height()),
                8.0, 8.0,
            )
            painter.setClipPath(clip)
            painter.drawPixmap(dx, dy, scaled)
            painter.setClipping(False)

        # --- video badge ---
        if media_type == "video":
            bs = 30
            bx = thumb_rect.right() - bs - 6
            by = thumb_rect.bottom() - bs - 6
            badge = QPainterPath()
            badge.addRoundedRect(float(bx), float(by), float(bs), float(bs), 6.0, 6.0)
            painter.fillPath(badge, QBrush(QColor(0, 0, 0, 170)))
            # play triangle
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#ffffff")))
            tri = QPainterPath()
            cx, cy = bx + bs / 2, by + bs / 2
            tri.moveTo(cx - 4, cy - 6)
            tri.lineTo(cx + 6, cy)
            tri.lineTo(cx - 4, cy + 6)
            tri.closeSubpath()
            painter.drawPath(tri)

        # --- selection checkmark ---
        if app_sel:
            cs = 24
            cxp = thumb_rect.right() - cs + 4
            cyp = thumb_rect.y() - 2
            circle = QPainterPath()
            circle.addEllipse(float(cxp), float(cyp), float(cs), float(cs))
            painter.fillPath(circle, QBrush(QColor("#7c5cfc")))
            painter.setPen(QPen(QColor("#ffffff"), 2.2))
            painter.drawLine(cxp + 6, cyp + 12, cxp + 10, cyp + 17)
            painter.drawLine(cxp + 10, cyp + 17, cxp + 18, cyp + 7)

        # --- filename text ---
        text_rect = QRect(rect.x() + 6, thumb_rect.bottom() + 4, rect.width() - 12, 28)
        painter.setPen(QColor("#b8b8d0"))
        painter.setFont(QFont("Segoe UI", 9))
        raw = index.data(Qt.ItemDataRole.DisplayRole) or ""
        elided = painter.fontMetrics().elidedText(
            raw, Qt.TextElideMode.ElideMiddle, text_rect.width()
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, elided)

        painter.restore()

    def sizeHint(self, option, index):
        if index.data(ROLE_DATE_HEADER):
            parent = self.parent()
            vw = parent.viewport().width() if parent else 1200
            return QSize(vw, DATE_HEADER_H)
        return ITEM_SIZE


# ────────────────────────────────────────────────────────────────
#  Gallery list widget
# ────────────────────────────────────────────────────────────────

class GalleryWidget(QListWidget):
    """Scrollable grid of media thumbnails."""

    item_activated = Signal(str)       # double-click / enter → open viewer
    item_toggle_select = Signal(str)   # ctrl-click → toggle selection

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSpacing(8)
        self.setUniformItemSizes(False)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.setMouseTracking(True)
        self.setWrapping(True)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._delegate = ThumbnailDelegate(self)
        self.setItemDelegate(self._delegate)

        self._path_items: dict[str, QListWidgetItem] = {}

        self.itemClicked.connect(self._on_click)

    # ---- public API ----

    def add_date_header(self, date_str: str):
        """Insert a full-width date separator row."""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.DisplayRole, date_str)
        item.setData(ROLE_DATE_HEADER, True)
        item.setFlags(Qt.ItemFlag.NoItemFlags)  # not selectable/clickable
        # Do NOT call setSizeHint — the delegate computes it dynamically
        self.addItem(item)

    def add_media_item(self, name: str, path: str, media_type: str):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.DisplayRole, name)
        item.setData(ROLE_PATH, path)
        item.setData(ROLE_MEDIA_TYPE, media_type)
        item.setData(ROLE_LOADED, False)
        item.setData(ROLE_APP_SELECTED, False)
        item.setSizeHint(ITEM_SIZE)
        self.addItem(item)
        self._path_items[path] = item

    def set_thumbnail(self, path: str, qimage: QImage):
        item = self._path_items.get(path)
        if item:
            item.setIcon(QIcon(QPixmap.fromImage(qimage)))
            item.setData(ROLE_LOADED, True)

    def set_thumbnail_pixmap(self, path: str, pm: QPixmap):
        item = self._path_items.get(path)
        if item:
            item.setIcon(QIcon(pm))
            item.setData(ROLE_LOADED, True)

    def toggle_selection(self, path: str) -> bool:
        item = self._path_items.get(path)
        if item:
            cur = bool(item.data(ROLE_APP_SELECTED))
            item.setData(ROLE_APP_SELECTED, not cur)
            self.viewport().update()
            return not cur
        return False

    def set_selection(self, path: str, selected: bool):
        item = self._path_items.get(path)
        if item:
            item.setData(ROLE_APP_SELECTED, selected)
            self.viewport().update()

    def get_selected_paths(self) -> list[str]:
        return [
            self.item(i).data(ROLE_PATH)
            for i in range(self.count())
            if self.item(i).data(ROLE_APP_SELECTED)
        ]

    def clear_all_selection(self):
        for i in range(self.count()):
            self.item(i).setData(ROLE_APP_SELECTED, False)
        self.viewport().update()

    def remove_by_path(self, path: str):
        item = self._path_items.pop(path, None)
        if item:
            self.takeItem(self.row(item))

    def clear_gallery(self):
        self.clear()
        self._path_items.clear()

    def get_all_paths(self) -> list[str]:
        return [
            p for i in range(self.count())
            if (p := self.item(i).data(ROLE_PATH))
        ]

    def path_exists(self, path: str) -> bool:
        return path in self._path_items

    # ---- signals ----

    def _on_click(self, item: QListWidgetItem):
        if item.data(ROLE_DATE_HEADER):
            return
        path = item.data(ROLE_PATH)
        if not path:
            return
        mods = QApplication.keyboardModifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            self.item_toggle_select.emit(path)
        else:
            self.item_activated.emit(path)

