"""
Ash Album — Data models.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MediaItem:
    """Represents a single media file discovered on disk."""

    path: str
    name: str
    media_type: str  # "photo" | "video"
    created: float  # timestamp (st_ctime)
    modified: float  # timestamp (st_mtime)
    size: int  # bytes
    folder: str  # display name of parent folder (e.g. "Screenshots")
    folder_path: str  # absolute path of parent folder

    @classmethod
    def from_path(cls, filepath: str) -> MediaItem | None:
        from .config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

        p = Path(filepath)
        try:
            stat = p.stat()
        except OSError:
            return None

        ext = p.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            media_type = "photo"
        elif ext in VIDEO_EXTENSIONS:
            media_type = "video"
        else:
            return None

        return cls(
            path=str(p),
            name=p.name,
            media_type=media_type,
            created=stat.st_ctime,
            modified=stat.st_mtime,
            size=stat.st_size,
            folder=p.parent.name,
            folder_path=str(p.parent),
        )
