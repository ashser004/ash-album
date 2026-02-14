"""
Ash Album — Media operations: delete, hide, unhide, restore.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from send2trash import send2trash


class MediaOperations:
    """Handles file deletion (recycle-bin) and hide/unhide logic."""

    def __init__(self, hidden_dir: str | Path):
        self.hidden_dir = Path(hidden_dir)
        self.hidden_dir.mkdir(parents=True, exist_ok=True)
        self.deleted_this_session: list[dict] = []
        self._hidden_map: dict[str, str] = {}  # hidden_path → original_path
        self._load_map()

    # ---- Delete ----

    def delete_to_trash(self, file_path: str) -> bool:
        """Send *file_path* to the Windows Recycle Bin."""
        try:
            name = Path(file_path).name
            send2trash(file_path)
            self.deleted_this_session.append({
                "path": file_path,
                "name": name,
                "time": datetime.now().isoformat(),
            })
            return True
        except Exception:
            return False

    # ---- Hide / unhide ----

    def hide_file(self, file_path: str) -> str | None:
        """Move file into the hidden directory. Returns new path or None."""
        try:
            src = Path(file_path)
            dst = self.hidden_dir / src.name
            dst = self._unique_dst(dst)
            shutil.move(str(src), str(dst))
            self._hidden_map[str(dst)] = str(src)
            self._save_map()
            return str(dst)
        except Exception:
            return None

    def unhide_file(self, hidden_path: str) -> str | None:
        """Move file back to its original location. Returns restored path."""
        try:
            original = self._hidden_map.get(str(hidden_path))
            if not original:
                return None
            dst = Path(original)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst = self._unique_dst(dst)
            shutil.move(str(hidden_path), str(dst))
            del self._hidden_map[str(hidden_path)]
            self._save_map()
            return str(dst)
        except Exception:
            return None

    def get_hidden_files(self) -> list[str]:
        """Return paths of all files currently hidden."""
        result = []
        if self.hidden_dir.exists():
            for f in self.hidden_dir.iterdir():
                if f.is_file() and f.name != ".hidden_map.json":
                    result.append(str(f))
        return result

    def get_deleted_this_session(self) -> list[dict]:
        return list(self.deleted_this_session)

    # ---- internal persistence ----

    def _map_file(self) -> Path:
        return self.hidden_dir / ".hidden_map.json"

    def _load_map(self):
        mf = self._map_file()
        if mf.exists():
            try:
                with open(mf, "r", encoding="utf-8") as fh:
                    self._hidden_map = json.load(fh)
            except Exception:
                self._hidden_map = {}

    def _save_map(self):
        with open(self._map_file(), "w", encoding="utf-8") as fh:
            json.dump(self._hidden_map, fh, indent=2)

    @staticmethod
    def _unique_dst(dst: Path) -> Path:
        """If *dst* already exists, append a numeric suffix."""
        if not dst.exists():
            return dst
        stem, suffix = dst.stem, dst.suffix
        i = 1
        while dst.exists():
            dst = dst.parent / f"{stem}_{i}{suffix}"
            i += 1
        return dst
