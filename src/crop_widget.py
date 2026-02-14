"""
Ash Album — Crop dialog with rubber-band rectangle selection.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from PIL import Image as PILImage

from .theme import COLORS


# ────────────────────────────────────────────────────────────
#  Canvas that lets the user draw a crop rectangle
# ────────────────────────────────────────────────────────────

class _CropCanvas(QWidget):
    """Displays an image and lets the user draw a selection rectangle."""

    selection_changed = Signal(QRect)   # rect in *original-image* coords

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._src_pm = pixmap
        self._sel = QRect()             # selection in widget coords
        self._drawing = False
        self._origin = QPoint()

        # Computed each paint
        self._img_rect = QRect()        # where the image is drawn
        self._scale = 1.0

        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ---- mouse events ----

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._origin = ev.pos()
            self._sel = QRect(self._origin, self._origin)
            self._drawing = True
            self.update()

    def mouseMoveEvent(self, ev):
        if self._drawing:
            self._sel = QRect(self._origin, ev.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            self.update()
            self.selection_changed.emit(self._map_to_original(self._sel))

    # ---- painting ----

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Black background
        p.fillRect(self.rect(), QColor("#0a0a12"))

        # Scale image to fit
        scaled = self._src_pm.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        dx = (self.width() - scaled.width()) // 2
        dy = (self.height() - scaled.height()) // 2
        self._img_rect = QRect(dx, dy, scaled.width(), scaled.height())
        self._scale = self._src_pm.width() / scaled.width() if scaled.width() else 1.0
        p.drawPixmap(dx, dy, scaled)

        # Dim overlay outside selection
        if not self._sel.isNull() and self._sel.width() > 2 and self._sel.height() > 2:
            overlay = QPainterPath()
            overlay.addRect(float(self.rect().x()), float(self.rect().y()),
                            float(self.rect().width()), float(self.rect().height()))
            hole = QPainterPath()
            hole.addRect(float(self._sel.x()), float(self._sel.y()),
                         float(self._sel.width()), float(self._sel.height()))
            overlay = overlay.subtracted(hole)
            p.fillPath(overlay, QBrush(QColor(0, 0, 0, 140)))

            # Selection border
            p.setPen(QPen(QColor(COLORS["accent"]), 2, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self._sel)

        p.end()

    # ---- coord mapping ----

    def _map_to_original(self, r: QRect) -> QRect:
        """Map widget-space rect to original-image pixel coords."""
        # Clamp to image area
        clamped = r.intersected(self._img_rect)
        if clamped.isNull():
            return QRect()
        ox = int((clamped.x() - self._img_rect.x()) * self._scale)
        oy = int((clamped.y() - self._img_rect.y()) * self._scale)
        ow = int(clamped.width() * self._scale)
        oh = int(clamped.height() * self._scale)
        return QRect(ox, oy, ow, oh)

    def get_selection_original(self) -> QRect:
        return self._map_to_original(self._sel)


# ────────────────────────────────────────────────────────────
#  Crop dialog
# ────────────────────────────────────────────────────────────

class CropDialog(QDialog):
    """Shows an image and lets the user crop it, choosing to overwrite or
    save as a new file.  Emits *cropped* with the saved file path."""

    cropped = Signal(str)  # saved path

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop Image")
        self.setMinimumSize(800, 560)
        self._path = image_path
        self._last_rect = QRect()

        self._build_ui()
        self.showMaximized()

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg_darkest']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Canvas
        pm = QPixmap(self._path)
        self._canvas = _CropCanvas(pm, self)
        self._canvas.selection_changed.connect(self._on_selection)
        root.addWidget(self._canvas, 1)

        # Bottom bar
        bar = QWidget()
        bar.setFixedHeight(60)
        bar.setStyleSheet(f"background-color: {COLORS['bg_mid']};")
        blay = QHBoxLayout(bar)
        blay.setContentsMargins(16, 0, 16, 0)
        blay.setSpacing(12)

        self._info = QLabel("Draw a rectangle on the image to crop")
        self._info.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 12px;")

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        self._btn_overwrite = QPushButton("Overwrite Original")
        self._btn_overwrite.setObjectName("dangerBtn")
        self._btn_overwrite.setEnabled(False)
        self._btn_overwrite.clicked.connect(self._do_overwrite)

        self._btn_saveas = QPushButton("Save as New File")
        self._btn_saveas.setObjectName("accentBtn")
        self._btn_saveas.setEnabled(False)
        self._btn_saveas.clicked.connect(self._do_save_as)

        blay.addWidget(self._info, 1)
        blay.addWidget(btn_cancel)
        blay.addWidget(self._btn_overwrite)
        blay.addWidget(self._btn_saveas)

        root.addWidget(bar)

    # ---- slots ----

    def _on_selection(self, rect: QRect):
        self._last_rect = rect
        valid = rect.width() > 4 and rect.height() > 4
        self._btn_overwrite.setEnabled(valid)
        self._btn_saveas.setEnabled(valid)
        if valid:
            self._info.setText(
                f"Selection: {rect.width()} × {rect.height()} "
                f"at ({rect.x()}, {rect.y()})"
            )
        else:
            self._info.setText("Selection too small — draw again")

    def _crop_image(self) -> PILImage.Image | None:
        r = self._last_rect   # use the rect captured at mouse-release time
        if r.isNull() or r.width() < 2 or r.height() < 2:
            return None
        try:
            img = PILImage.open(self._path)
            box = (r.x(), r.y(), r.x() + r.width(), r.y() + r.height())
            return img.crop(box)
        except Exception:
            return None

    def _do_overwrite(self):
        cropped = self._crop_image()
        if cropped is None:
            return
        try:
            cropped.save(self._path)
            self.cropped.emit(self._path)
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not save:\n{exc}")

    def _do_save_as(self):
        cropped = self._crop_image()
        if cropped is None:
            return
        p = Path(self._path)
        default_name = f"{p.stem}_cropped{p.suffix}"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save cropped image",
            str(p.parent / default_name),
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)",
        )
        if not save_path:
            return
        try:
            cropped.save(save_path)
            self.cropped.emit(save_path)
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not save:\n{exc}")
