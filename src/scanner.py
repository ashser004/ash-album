"""
Ash Album — Background media scanner.

Recursively scans configured folders for image/video files and emits
discovered MediaItem objects in batches for UI consumption.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, SCAN_FOLDERS
from .models import MediaItem

# Folders we never descend into
_SKIP_DIRS = frozenset({
    "$RECYCLE.BIN",
    "System Volume Information",
    "AppData",
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
})

BATCH_SIZE = 40  # emit items in batches for fewer signals


class ScannerWorker(QThread):
    """Scans folders on a background thread and emits batches of MediaItem."""

    items_found = Signal(list)          # list[MediaItem]
    scan_progress = Signal(str)         # human-readable status
    scan_finished = Signal(int)         # total count

    def __init__(
        self,
        scan_folders: list[Path] | None = None,
        hidden_dir: Path | None = None,
    ):
        super().__init__()
        self.scan_folders = scan_folders or list(SCAN_FOLDERS)
        self.hidden_dir = hidden_dir
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        count = 0
        batch: list[MediaItem] = []
        visited: set[str] = set()
        all_ext = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

        for folder in self.scan_folders:
            if self._stop:
                break
            folder = Path(folder)
            if not folder.exists() or not folder.is_dir():
                continue

            self.scan_progress.emit(f"Scanning {folder.name}…")

            for root, dirs, files in os.walk(folder, topdown=True):
                if self._stop:
                    break

                root_path = Path(root)

                # Skip the hidden directory
                if self.hidden_dir:
                    try:
                        root_path.relative_to(self.hidden_dir)
                        dirs.clear()
                        continue
                    except ValueError:
                        pass

                # Prune unwanted subdirectories
                dirs[:] = [
                    d for d in dirs
                    if d not in _SKIP_DIRS and not d.startswith(".")
                ]

                for fname in files:
                    if self._stop:
                        break

                    fpath = root_path / fname
                    ext = fpath.suffix.lower()
                    if ext not in all_ext:
                        continue

                    # Deduplicate across overlapping scan roots
                    try:
                        resolved = str(fpath.resolve())
                    except OSError:
                        continue
                    if resolved in visited:
                        continue
                    visited.add(resolved)

                    item = MediaItem.from_path(resolved)
                    if item is None:
                        continue

                    batch.append(item)
                    count += 1

                    if len(batch) >= BATCH_SIZE:
                        self.items_found.emit(batch)
                        batch = []

        # Flush remaining
        if batch:
            self.items_found.emit(batch)

        self.scan_finished.emit(count)
