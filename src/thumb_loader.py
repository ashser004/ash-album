"""
Ash Album — Background thumbnail generator with disk cache.

Uses a dedicated QThread that processes a work queue.  Thumbnails are
saved to the cache directory so subsequent launches are fast.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition
from PySide6.QtGui import QImage

from PIL import Image as PILImage

from .config import VIDEO_EXTENSIONS, THUMB_SIZE


class ThumbnailWorker(QThread):
    """Generates thumbnails for media files on a background thread."""

    thumbnail_ready = Signal(str, QImage)  # (file_path, thumb)

    def __init__(self, cache_dir: str | Path, thumb_size: int = THUMB_SIZE):
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumb_size = thumb_size

        self._queue: list[str] = []
        self._mutex = QMutex()
        self._cond = QWaitCondition()
        self._stop = False
        self._processed: set[str] = set()

    # ---- public queue API ----

    def enqueue(self, file_path: str):
        self._mutex.lock()
        if file_path not in self._processed and file_path not in self._queue:
            self._queue.append(file_path)
            self._cond.wakeOne()
        self._mutex.unlock()

    def enqueue_batch(self, paths: list[str]):
        self._mutex.lock()
        for fp in paths:
            if fp not in self._processed and fp not in self._queue:
                self._queue.append(fp)
        self._cond.wakeOne()
        self._mutex.unlock()

    def prioritize(self, paths: list[str]):
        """Move *paths* to the front of the queue (for visible-area loading)."""
        self._mutex.lock()
        pset = set(paths)
        front = [p for p in paths if p in set(self._queue)]
        rest = [p for p in self._queue if p not in pset]
        self._queue = front + rest
        self._cond.wakeOne()
        self._mutex.unlock()

    def invalidate(self, path: str):
        """Remove *path* from the processed set so it can be re-generated."""
        self._mutex.lock()
        self._processed.discard(path)
        self._mutex.unlock()

    def stop(self):
        self._stop = True
        self._mutex.lock()
        self._cond.wakeAll()
        self._mutex.unlock()

    # ---- thread entry ----

    def run(self):
        while not self._stop:
            self._mutex.lock()
            while not self._queue and not self._stop:
                self._cond.wait(self._mutex)
            if self._stop:
                self._mutex.unlock()
                break
            file_path = self._queue.pop(0) if self._queue else None
            self._mutex.unlock()

            if file_path is None or file_path in self._processed:
                continue
            self._processed.add(file_path)

            try:
                img = self._load_or_generate(file_path)
                if img and not img.isNull():
                    self.thumbnail_ready.emit(file_path, img)
            except Exception:
                pass

    # ---- generation helpers ----

    def _cache_path(self, file_path: str) -> Path:
        h = hashlib.md5(file_path.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.jpg"

    def _load_or_generate(self, file_path: str) -> QImage | None:
        cp = self._cache_path(file_path)
        if cp.exists():
            img = QImage(str(cp))
            if not img.isNull():
                return img

        ext = Path(file_path).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            img = self._video_thumb(file_path)
        else:
            img = self._image_thumb(file_path)

        if img and not img.isNull():
            img.save(str(cp), "JPEG", 85)
        return img

    def _image_thumb(self, file_path: str) -> QImage | None:
        try:
            with PILImage.open(file_path) as pil:
                pil.thumbnail((self.thumb_size, self.thumb_size), PILImage.LANCZOS)
                if pil.mode == "RGBA":
                    bg = PILImage.new("RGB", pil.size, (24, 24, 40))
                    bg.paste(pil, mask=pil.split()[3])
                    pil = bg
                elif pil.mode != "RGB":
                    pil = pil.convert("RGB")
                data = pil.tobytes("raw", "RGB")
                qimg = QImage(
                    data, pil.width, pil.height,
                    pil.width * 3, QImage.Format.Format_RGB888,
                )
                return qimg.copy()
        except Exception:
            return None

    def _video_thumb(self, file_path: str) -> QImage | None:
        try:
            import cv2
        except ImportError:
            return None
        try:
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                return None

            h, w = frame.shape[:2]
            scale = self.thumb_size / max(h, w)
            nw, nh = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            qimg = QImage(
                frame.data, nw, nh, nw * 3, QImage.Format.Format_RGB888,
            )
            return qimg.copy()
        except Exception:
            return None
