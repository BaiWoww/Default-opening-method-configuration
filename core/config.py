"""JSON-backed persistence for user presets.

Stored at %APPDATA%\\DefaultOpener\\config.json so it survives moves of the exe.
"""
from __future__ import annotations

import json
import os
from typing import Dict

from .models import ExtensionConfig

APP_DIRNAME = "DefaultOpener"
CONFIG_FILENAME = "config.json"


def app_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_DIRNAME)
    os.makedirs(path, exist_ok=True)
    return path


def config_path() -> str:
    return os.path.join(app_dir(), CONFIG_FILENAME)


def load_all() -> Dict[str, ExtensionConfig]:
    path = config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    out: Dict[str, ExtensionConfig] = {}
    for ext, data in raw.items():
        try:
            out[ext.lower()] = ExtensionConfig.from_dict(ext, data)
        except Exception:
            continue
    return out


def save_all(data: Dict[str, ExtensionConfig]) -> bool:
    path = config_path()
    try:
        serializable = {ext: cfg.to_dict() for ext, cfg in data.items()}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except OSError as e:
        print(f"[config] save failed: {e}")
        return False
