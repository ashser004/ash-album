"""
Ash Album — Default-app detection and registration helpers.

Supports Windows 10/11 and Linux (Debian / Ubuntu / Mint).
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys

# Suppress console window for subprocess calls on Windows
_CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0


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
    """Check whether Ash Album is the default handler on Windows.

    Uses multiple strategies so it works regardless of how the default
    was set (installer ProgId, Open-with dialog, Settings panel, etc.):
      1. Read the UserChoice ProgId and compare to known values.
      2. Resolve the ProgId's shell\\open\\command and look for our exe.
      3. Fallback: query with ``reg.exe`` if winreg fails in frozen builds.
    """
    # Strategy A — winreg
    result = _win_check_via_winreg()
    if result is not None:
        return result

    # Strategy B — subprocess ``reg query`` (works even if winreg is
    # unavailable or broken in PyInstaller bundles)
    return _win_check_via_subprocess()


def _win_check_via_winreg() -> bool | None:
    """Return True/False via winreg, or None if winreg isn't usable."""
    try:
        import winreg
    except ImportError:
        return None

    _KNOWN = {
        _WINDOWS_PROGID.lower(),            # ashalbum.image
        "applications\\ash album.exe",
        "ashalbum",
    }

    for ext in TARGET_EXTENSIONS:
        try:
            uc_path = (
                rf"Software\Microsoft\Windows\CurrentVersion\Explorer"
                rf"\FileExts\{ext}\UserChoice"
            )
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uc_path) as key:
                prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        except OSError:
            return False

        low = prog_id.lower()

        # Fast match on known ProgIds
        if low in _KNOWN:
            continue
        # Substring match (covers e.g. "AppXxyz..." with embedded name)
        if "ashalbum" in low or "ash album" in low:
            continue

        # Resolve the ProgId → shell\open\command
        cmd = _win_resolve_command(prog_id, winreg)
        if cmd and "ash album" in cmd.lower():
            continue

        return False

    return True


def _win_resolve_command(prog_id: str, winreg) -> str:
    """Return the shell\\open\\command string for *prog_id*, or ''.
    
    Handles both normal ProgIds and Windows 10/11 AppX hashed ProgIds.
    """
    # For AppX hashes, the command is in HKCR under the hash itself
    paths = [
        (winreg.HKEY_CLASSES_ROOT,  rf"{prog_id}\shell\open\command"),
        (winreg.HKEY_CURRENT_USER,  rf"Software\Classes\{prog_id}\shell\open\command"),
        # Sometimes AppX points to an Application.Reference
        (winreg.HKEY_CLASSES_ROOT,  rf"{prog_id}\Application"),
    ]
    
    for hive, path in paths:
        try:
            with winreg.OpenKey(hive, path) as key:
                # Try default value first
                try:
                    cmd, _ = winreg.QueryValueEx(key, "")
                    if cmd:
                        return cmd
                except OSError:
                    pass
                # For Application keys, check DelegateExecute or ApplicationName
                try:
                    val, _ = winreg.QueryValueEx(key, "ApplicationName")
                    if val:
                        return val
                except OSError:
                    pass
        except OSError:
            continue
    
    return ""


def _win_check_via_subprocess() -> bool:
    """Fallback: query the actual executable path for AppX and other ProgIds.
    
    Reads the shell\\open\\command directly from the ProgId stored in UserChoice,
    including AppX hashed ProgIds that Windows 10/11 create.
    """
    for ext in TARGET_EXTENSIONS:
        try:
            # Get the ProgId from UserChoice
            result = subprocess.run(
                [
                    "reg", "query",
                    rf"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\UserChoice",
                    "/v", "ProgId",
                ],
                capture_output=True, text=True, timeout=5, creationflags=_CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                return False
            
            # Extract ProgId value from output
            for line in result.stdout.splitlines():
                if "ProgId" in line and "REG_SZ" in line:
                    parts = line.split("REG_SZ", 1)
                    if len(parts) == 2:
                        prog_id = parts[1].strip()
                        break
            else:
                return False
            
            # Now query the shell\open\command for this ProgId
            result = subprocess.run(
                [
                    "reg", "query",
                    rf"HKCR\{prog_id}\shell\open\command",
                    "/ve",  # query default value
                ],
                capture_output=True, text=True, timeout=5, creationflags=_CREATE_NO_WINDOW
            )
            
            output_lower = result.stdout.lower()
            
            # Check if the command points to our exe
            if "ash album" in output_lower or "ashalbum" in output_lower:
                continue
            
            return False
            
        except Exception:
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
