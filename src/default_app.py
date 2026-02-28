"""
Ash Album — Default-app detection and registration helpers.

Supports Windows 10/11 and Linux (Debian / Ubuntu / Mint).
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys


# Extensions we care about
TARGET_EXTENSIONS = (".jpg", ".jpeg", ".png")

# Our ProgId — must match what the Inno Setup installer registers
_WINDOWS_PROGID = "AshAlbum.Image"

# Desktop entry name used on Linux .deb installs
_LINUX_DESKTOP_ENTRY = "ash-album.desktop"

# Mime types that correspond to our target extensions
_LINUX_MIME_TYPES = [
    "image/jpeg",
    "image/png",
]


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _is_linux() -> bool:
    return platform.system() == "Linux"


# ------------------------------------------------------------------
#  Detection — is Ash Album the default handler?
# ------------------------------------------------------------------

def is_default_for_images() -> bool:
    """Return True if Ash Album is registered as the default handler
    for *all* of .jpg, .jpeg, and .png."""
    if _is_windows():
        return _win_is_default()
    if _is_linux():
        return _linux_is_default()
    return False  # unsupported platform — assume no


def _win_is_default() -> bool:
    """Check the Windows UserChoice registry keys."""
    try:
        import winreg
    except ImportError:
        return False

    for ext in TARGET_EXTENSIONS:
        try:
            key_path = (
                rf"Software\Microsoft\Windows\CurrentVersion\Explorer"
                rf"\FileExts\{ext}\UserChoice"
            )
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                prog_id, _ = winreg.QueryValueEx(key, "ProgId")
                if prog_id != _WINDOWS_PROGID:
                    return False
        except (OSError, FileNotFoundError):
            return False
    return True


def _linux_is_default() -> bool:
    """Check via xdg-mime query."""
    for mime in _LINUX_MIME_TYPES:
        try:
            result = subprocess.run(
                ["xdg-mime", "query", "default", mime],
                capture_output=True, text=True, timeout=5,
            )
            if _LINUX_DESKTOP_ENTRY not in result.stdout.strip():
                return False
        except Exception:
            return False
    return True


# ------------------------------------------------------------------
#  Open the system *Default Apps* settings panel
# ------------------------------------------------------------------

def open_default_apps_settings() -> bool:
    """Open the OS settings page where the user can pick default apps.
    Returns True if the action was launched successfully."""
    if _is_windows():
        return _win_open_settings()
    if _is_linux():
        return _linux_open_settings()
    return False


def _win_open_settings() -> bool:
    """Open Windows 10/11 Default Apps settings panel."""
    try:
        os.startfile("ms-settings:defaultapps")  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def _linux_open_settings() -> bool:
    """Try to open the relevant settings panel on GNOME / Cinnamon / KDE."""
    # Try GNOME / Cinnamon first
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    cmds_to_try: list[list[str]] = []

    if "gnome" in desktop or "cinnamon" in desktop or "unity" in desktop:
        cmds_to_try.append(["gnome-control-center", "default-apps"])

    if "kde" in desktop:
        cmds_to_try.append(["systemsettings5", "kcm_componentchooser"])

    # Fallback: xdg-open settings (works on some distros)
    cmds_to_try.append(["xdg-open", "settings://default-apps"])

    for cmd in cmds_to_try:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            continue

    # Last resort: try to set defaults directly via xdg-mime
    return _linux_set_default()


def _linux_set_default() -> bool:
    """Register Ash Album as default for our mime types via xdg-mime."""
    success = True
    for mime in _LINUX_MIME_TYPES:
        try:
            subprocess.run(
                ["xdg-mime", "default", _LINUX_DESKTOP_ENTRY, mime],
                capture_output=True, timeout=5,
            )
        except Exception:
            success = False
    return success
