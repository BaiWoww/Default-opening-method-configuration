"""HKCU registry read/write for file associations.

Writes to HKCU\\Software\\Classes which overrides system defaults for the
current user without requiring administrator rights.
"""
from __future__ import annotations

import re
import winreg
from typing import Dict, List, Optional, Tuple

HKCU_CLASSES = winreg.HKEY_CURRENT_USER
HKCR = winreg.HKEY_CLASSES_ROOT
CLASSES_SUBKEY = r"Software\Classes"
PROGID_PREFIX = "DefaultOpener."

# Regex to extract exe path from a command string like:
#   "C:\path\foo.exe" "%1"
#   "C:\path\foo.exe" --opt "%1"
#   C:\path\foo.exe "%1"
_PATH_RE = re.compile(r'^\s*"?([A-Za-z]:[\\/][^"]*?\.(?:exe|EXE))')


def progid_for(ext: str) -> str:
    e = ext.lower().lstrip(".")
    return f"{PROGID_PREFIX}{e}file"


def list_extensions_with_defaults() -> Dict[str, str]:
    """Return {ext: progid} for every associated extension visible to the user.

    Reads HKEY_CLASSES_ROOT which is the merged view of HKCU\\Software\\Classes
    and HKLM\\Software\\Classes (HKCU takes precedence).
    """
    result: Dict[str, str] = {}
    try:
        with winreg.OpenKey(HKCR, "") as root:
            i = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(root, i)
                except OSError:
                    break
                if sub_name.startswith("."):
                    try:
                        with winreg.OpenKey(root, sub_name) as k:
                            value, _ = winreg.QueryValueEx(k, "")
                            if value:
                                result[sub_name.lower()] = value
                    except FileNotFoundError:
                        pass
                i += 1
    except FileNotFoundError:
        pass
    return result


def get_progid_command(progid: str) -> Optional[str]:
    """Return the (default) command line for a ProgID's shell\\open\\command.

    Reads from HKEY_CLASSES_ROOT (merged view).
    """
    key_path = f"{progid}\\shell\\open\\command"
    try:
        with winreg.OpenKey(HKCR, key_path) as k:
            value, _ = winreg.QueryValueEx(k, "")
            return value
    except FileNotFoundError:
        return None


def get_progid_friendly_name(progid: str) -> str:
    """Read the (default) value of the ProgID key (friendly name)."""
    key_path = progid
    try:
        with winreg.OpenKey(HKCR, key_path) as k:
            value, _ = winreg.QueryValueEx(k, "")
            return value or progid
    except FileNotFoundError:
        return progid


def _create_subkey(parent, path: str):
    return winreg.CreateKeyEx(parent, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)


def set_association(ext: str, progid: str, command: str, friendly_name: str = "") -> bool:
    """Set HKCU default for `ext` -> `progid` and write its open command.

    Returns True on success.
    """
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    try:
        with _create_subkey(HKCU_CLASSES, CLASSES_SUBKEY) as _:
            pass
        with _create_subkey(HKCU_CLASSES, f"{CLASSES_SUBKEY}\\{ext}") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, progid)

        with _create_subkey(HKCU_CLASSES, f"{CLASSES_SUBKEY}\\{progid}") as k:
            if friendly_name:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, friendly_name)

        with _create_subkey(HKCU_CLASSES, f"{CLASSES_SUBKEY}\\{progid}\\shell\\open\\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, command)
        return True
    except OSError as e:
        print(f"[registry] set_association failed: {e}")
        return False


def extract_exe_path(command: str) -> str:
    """Pull the exe path out of a command-line string for display."""
    if not command:
        return ""
    m = _PATH_RE.match(command)
    if m:
        return m.group(1)
    # fallback: trim trailing args crudely
    s = command.strip().strip('"')
    return s


def get_current_default(ext: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """For an extension, return (progid, command, exe_path) or (None, None, None)."""
    ext = ext.lower()
    exts = list_extensions_with_defaults()
    progid = exts.get(ext)
    if not progid:
        return None, None, None
    cmd = get_progid_command(progid)
    exe = extract_exe_path(cmd) if cmd else None
    return progid, cmd, exe


def refresh_shell() -> None:
    """Best-effort: notify the shell of association changes (SHChangeNotify).

    This helps File Explorer refresh icons quickly. Failures are non-fatal.
    """
    try:
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0)
    except Exception:
        pass


def remove_user_override(ext: str) -> bool:
    """Remove the HKCU override for `ext` so the system default takes effect.

    Deletes the `HKCU\\Software\\Classes\\<ext>` key and the tool-generated
    ProgID key (`DefaultOpener.<ext>file`). Returns True if anything was
    removed. Non-existent keys are not errors.
    """
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    progid = progid_for(ext)

    def _del_tree(root, path: str) -> bool:
        removed = False
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
                subs = []
                i = 0
                while True:
                    try:
                        subs.append(winreg.EnumKey(k, i))
                    except OSError:
                        break
                    i += 1
            for s in subs:
                _del_tree(root, path + "\\" + s)
            winreg.DeleteKey(root, path)
            removed = True
        except FileNotFoundError:
            pass
        except OSError:
            pass
        return removed

    r1 = _del_tree(HKCU_CLASSES, f"{CLASSES_SUBKEY}\\{ext}")
    r2 = _del_tree(HKCU_CLASSES, f"{CLASSES_SUBKEY}\\{progid}")
    return r1 or r2


def has_user_override(ext: str) -> bool:
    """Return True if the user has an HKCU override for `ext`."""
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    try:
        with winreg.OpenKey(HKCU_CLASSES, f"{CLASSES_SUBKEY}\\{ext}") as k:
            value, _ = winreg.QueryValueEx(k, "")
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False
