"""
Ash Album — Application configuration and paths.
"""

from __future__ import annotations

import json
from pathlib import Path

APP_NAME = "Ash Album"
APP_VERSION = "1.0.0"

DEFAULT_BASE_DIR = Path.home() / "Documents" / "AshAlbum"

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".mov", ".avi"})
ALL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

THUMB_SIZE = 180

SCAN_FOLDERS = [
    Path.home() / "Pictures",
    Path.home() / "Videos",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]

SCREENSHOTS_FOLDER = Path.home() / "Pictures" / "Screenshots"

SORT_OPTIONS = [
    ("Name (A → Z)", "name_asc"),
    ("Name (Z → A)", "name_desc"),
    ("Date Created (Newest First)", "created_desc"),
    ("Date Created (Oldest First)", "created_asc"),
    ("Date Modified (Newest First)", "modified_desc"),
    ("Date Modified (Oldest First)", "modified_asc"),
    ("File Size (Small → Large)", "size_asc"),
    ("File Size (Large → Small)", "size_desc"),
]


class AppConfig:
    """Manages application configuration persisted to disk."""

    def __init__(self):
        self.base_dir: Path = DEFAULT_BASE_DIR
        self._update_dirs()

    # ---- public API ----

    def load(self) -> bool:
        """Load config from disk. Returns True if config existed."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                self.base_dir = Path(data.get("base_dir", str(DEFAULT_BASE_DIR)))
                self._update_dirs()
                return True
            except Exception:
                pass
        return False

    def save(self):
        """Ensure directories exist and persist config."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hidden_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as fh:
            json.dump({"base_dir": str(self.base_dir)}, fh, indent=2)

    def set_base_dir(self, path: str | Path):
        self.base_dir = Path(path)
        self._update_dirs()

    def is_first_run(self) -> bool:
        return not self.config_file.exists()

    # ---- internal ----

    def _update_dirs(self):
        self.cache_dir: Path = self.base_dir / "cache"
        self.hidden_dir: Path = self.base_dir / "hidden"
        self.config_file: Path = self.base_dir / "config.json"
