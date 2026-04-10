"""
Ash Album — Update manifest, checking, downloading, and launch helpers.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/ashser004/ash-album/main/version.json"
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/ashser004/ash-album/releases/latest"
DEFAULT_INSTALLER_NAME = "Ash Album Setup.exe"
DOWNLOAD_CHUNK_SIZE = 64 * 1024
REQUEST_HEADERS = {
    "User-Agent": "Ash Album update checker",
    "Accept": "application/vnd.github+json",
}


@dataclass(slots=True)
class UpdateManifest:
    version: str
    download_url: str
    release_url: str = ""
    manifest_url: str = ""

    @property
    def installer_name(self) -> str:
        name = unquote(Path(urlparse(self.download_url).path).name.strip())
        return name or DEFAULT_INSTALLER_NAME


def _normalize_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip().lstrip("vV")
    cleaned = cleaned.split("-", 1)[0]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(remote_version: str, local_version: str) -> bool:
    return _normalize_version(remote_version) > _normalize_version(local_version)


def _release_download_url(version: str) -> str:
    cleaned = version.strip().lstrip("vV")
    return (
        f"https://github.com/ashser004/ash-album/releases/download/"
        f"v{cleaned}/{quote(DEFAULT_INSTALLER_NAME, safe='')}"
    )


def _release_page_url(version: str) -> str:
    cleaned = version.strip().lstrip("vV")
    return f"https://github.com/ashser004/ash-album/releases/tag/v{cleaned}"


def _read_json(url: str, timeout: int = 15) -> dict[str, Any]:
    request = Request(url, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _manifest_from_version_data(data: dict[str, Any], source_url: str) -> UpdateManifest:
    version = str(data.get("version", "")).strip()
    if not version:
        raise ValueError("version.json does not contain a version field")

    download_url = str(data.get("download_url") or _release_download_url(version))
    release_url = str(data.get("release_url") or _release_page_url(version))
    return UpdateManifest(
        version=version,
        download_url=download_url,
        release_url=release_url,
        manifest_url=source_url,
    )


def _manifest_from_latest_release(data: dict[str, Any], source_url: str) -> UpdateManifest:
    tag_name = str(data.get("tag_name", "")).strip()
    if not tag_name:
        raise ValueError("GitHub latest release response does not contain a tag_name")

    version = tag_name.lstrip("vV")
    download_url = _release_download_url(version)
    release_url = str(data.get("html_url") or _release_page_url(version))
    return UpdateManifest(
        version=version,
        download_url=download_url,
        release_url=release_url,
        manifest_url=source_url,
    )


def fetch_manifest(manifest_url: str = DEFAULT_MANIFEST_URL) -> UpdateManifest:
    errors: list[str] = []

    try:
        latest_release_data = _read_json(GITHUB_LATEST_RELEASE_URL)
        return _manifest_from_latest_release(latest_release_data, GITHUB_LATEST_RELEASE_URL)
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"latest release lookup: {exc}")

    try:
        version_data = _read_json(manifest_url)
        return _manifest_from_version_data(version_data, manifest_url)
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"manifest lookup: {exc}")

    raise ValueError("; ".join(errors) or "Could not fetch update information")


class UpdateCheckWorker(QThread):
    update_available = Signal(object)
    up_to_date = Signal()
    failed = Signal(str)

    def __init__(self, current_version: str, manifest_url: str = DEFAULT_MANIFEST_URL, parent=None):
        super().__init__(parent)
        self._current_version = current_version
        self._manifest_url = manifest_url

    def run(self):
        try:
            manifest = fetch_manifest(self._manifest_url)
            if is_newer_version(manifest.version, self._current_version):
                self.update_available.emit(manifest)
            else:
                self.up_to_date.emit()
        except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            self.failed.emit(str(exc))


class UpdateDownloadWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, download_url: str, target_path: str | Path, parent=None):
        super().__init__(parent)
        self._download_url = download_url
        self._target_path = Path(target_path)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        tmp_path = self._target_path.with_suffix(self._target_path.suffix + ".part")
        try:
            self._target_path.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(self._download_url, timeout=30) as response:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                if total > 0:
                    self.progress.emit(0, total)
                else:
                    self.progress.emit(0, 0)

                with open(tmp_path, "wb") as fh:
                    while not self._cancelled:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)

            if self._cancelled:
                raise RuntimeError("Download cancelled")

            os.replace(tmp_path, self._target_path)
            self.finished.emit(str(self._target_path))
        except (HTTPError, URLError, OSError, RuntimeError) as exc:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
            self.failed.emit(str(exc))


def cleanup_download_cache(download_dir: str | Path, remove_installers: bool = False):
    """Best-effort removal of cached update downloads.

    By default, only partial downloads are removed. Pass ``remove_installers``
    when the installer has already been launched and the cached .exe should be
    reclaimed.
    """
    folder = Path(download_dir)
    if not folder.exists():
        return
    for path in folder.iterdir():
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".part", ".tmp"} and not (remove_installers and suffix == ".exe"):
            continue
        try:
            path.unlink()
        except OSError:
            pass


def launch_installer(installer_path: str | Path) -> bool:
    path = str(installer_path)
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False
