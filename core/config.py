"""JSON-backed persistence for user presets and app settings.

Stored at %APPDATA%\\DefaultOpener\\config.json so it survives moves of the exe.
File layout:
    {
        "_settings": {"window": {...}, "recent_programs": [...]},
        ".py": {"presets": [...], ...},
        ...
}
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from .models import ExtensionConfig

APP_DIRNAME = "DefaultOpener"
CONFIG_FILENAME = "config.json"
SETTINGS_KEY = "_settings"
RECENT_PROGRAMS_MAX = 10


def app_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_DIRNAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(app_dir(), CONFIG_FILENAME)


def _load_raw() -> Dict[str, Any]:
    path = config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_raw(raw: Dict[str, Any]) -> bool:
    path = config_path()
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except OSError as e:
        print(f"[config] save failed: {e}")
        return False


def load_all() -> Dict[str, ExtensionConfig]:
    raw = _load_raw()
    out: Dict[str, ExtensionConfig] = {}
    for ext, data in raw.items():
        if ext == SETTINGS_KEY or not ext.startswith("."):
            continue
        if not isinstance(data, dict):
            continue
        try:
            out[ext.lower()] = ExtensionConfig.from_dict(ext, data)
        except Exception:
            continue
    return out


def save_all(data: Dict[str, ExtensionConfig]) -> bool:
    raw = _load_raw()
    # remove old extension entries, keep settings
    for k in list(raw.keys()):
        if k != SETTINGS_KEY:
            del raw[k]
    for ext, cfg in data.items():
        raw[ext.lower()] = cfg.to_dict()
    return _save_raw(raw)


def load_settings() -> Dict[str, Any]:
    raw = _load_raw()
    settings = raw.get(SETTINGS_KEY, {})
    return settings if isinstance(settings, dict) else {}


def save_settings(settings: Dict[str, Any]) -> bool:
    raw = _load_raw()
    raw[SETTINGS_KEY] = settings
    return _save_raw(raw)


def update_settings(updates: Dict[str, Any]) -> bool:
    settings = load_settings()
    settings.update(updates)
    return save_settings(settings)


def get_recent_programs() -> list:
    return load_settings().get("recent_programs", [])


def record_recent_program(path: str) -> bool:
    path = path.strip()
    if not path:
        return False
    programs = get_recent_programs()
    # dedup (case-insensitive on Windows)
    lower = [p.lower() for p in programs]
    if path.lower() in lower:
        programs = [p for p in programs if p.lower() != path.lower()]
    programs.insert(0, path)
    programs = programs[:RECENT_PROGRAMS_MAX]
    return update_settings({"recent_programs": programs})
