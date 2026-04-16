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

    def _failed_path(self, file_path: str) -> Path:
        h = hashlib.md5(file_path.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.failed"

    def _legacy_sig_path(self, file_path: str) -> Path:
        h = hashlib.md5(file_path.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{h}.sig"

    @staticmethod
    def _file_signature_from_stat(st) -> str:
        return f"{st.st_size}:{st.st_mtime_ns}"

    def _load_or_generate(self, file_path: str) -> QImage | None:
        cp = self._cache_path(file_path)
        sp = self._legacy_sig_path(file_path)
        fp = self._failed_path(file_path)
        source_path = Path(file_path)

        if not source_path.exists():
            for stale in (cp, sp, fp):
                if stale.exists():
                    try:
                        stale.unlink()
                    except OSError:
                        pass
            return None

        try:
            source_stat = source_path.stat()
        except OSError:
            return None
        signature = self._file_signature_from_stat(source_stat)

        # If this file previously failed thumbnail generation and has not changed,
        # skip re-decoding to avoid repeated noisy backend errors and slow rescans.
        if fp.exists() and signature:
            try:
                if fp.read_text(encoding="utf-8").strip() == signature:
                    return None
            except OSError:
                pass

        if cp.exists():
            # Fast-path cache validation based on mtime.
            # If source is newer than cached thumb, regenerate.
            cache_valid = False
            try:
                cache_valid = source_stat.st_mtime_ns <= cp.stat().st_mtime_ns
            except OSError:
                cache_valid = False

            if cache_valid:
                img = QImage(str(cp))
                if not img.isNull():
                    # Clean up one-time legacy sidecar if present.
                    if sp.exists():
                        try:
                            sp.unlink()
                        except OSError:
                            pass
                    if fp.exists():
                        try:
                            fp.unlink()
                        except OSError:
                            pass
                    return img
            else:
                for stale in (cp, sp):
                    if stale.exists():
                        try:
                            stale.unlink()
                        except OSError:
                            pass

        ext = source_path.suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            img = self._video_thumb(file_path)
        else:
            img = self._image_thumb(file_path)

        if img and not img.isNull():
            img.save(str(cp), "JPEG", 85)
            if sp.exists():
                try:
                    sp.unlink()
                except OSError:
                    pass
            if fp.exists():
                try:
                    fp.unlink()
                except OSError:
                    pass
        elif ext in VIDEO_EXTENSIONS and signature:
            if sp.exists():
                try:
                    sp.unlink()
                except OSError:
                    pass
            try:
                fp.write_text(signature, encoding="utf-8")
            except OSError:
                pass
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
            # Best-effort clamp of OpenCV logging for builds that ignore env vars.
            if hasattr(cv2, "setLogLevel"):
                level = getattr(cv2, "LOG_LEVEL_ERROR", None)
                if level is not None:
                    cv2.setLogLevel(level)
            elif hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
                log_mod = cv2.utils.logging
                if hasattr(log_mod, "setLogLevel") and hasattr(log_mod, "LOG_LEVEL_ERROR"):
                    log_mod.setLogLevel(log_mod.LOG_LEVEL_ERROR)
        except Exception:
            pass
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
