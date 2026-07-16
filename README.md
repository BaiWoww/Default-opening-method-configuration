# DefaultOpener

> A lightweight Windows GUI for managing **per-user** default file associations and switching between multiple "presets" for each file type — no admin rights required.

**English** · [简体中文](./README.zh-CN.md)

---

## Why?

Windows' built-in "Open with" dialog only lets you set **one** default app per file type, and configuring unknown extensions (e.g. `.xyz`) usually means diving into the registry. **DefaultOpener** makes both trivial — and lets you keep *multiple* "presets" (e.g. `VSCode`, `PyCharm`, `Notepad` for `.py`) so you can flip between them with a single click.

## Features

- 📋 Lists **every** associated extension visible to your user (~900+ on a typical Windows install)
- 🎯 Click an extension to see its current default program and a list of presets
- ⚡ One-click switch between presets — change `.py` from VSCode to PyCharm instantly
- ➕ Add new presets per extension (name, exe path, optional CLI args)
- 🆕 Register **unknown** file types (`.xyz`, `.foo`, …) with a custom program
- 🔒 Writes only to `HKEY_CURRENT_USER\Software\Classes` — **no admin required**
- 💾 Preset config persisted to `%APPDATA%\DefaultOpener\config.json`
- 🧪 Smoke tests for the registry + config layers

## Requirements

- Windows 10 / 11
- Python 3.8+ (for running from source)
- No external runtime dependencies for the built `.exe`

## Install (from source)

```bash
git clone https://github.com/BaiWoww/Default-opening-method-configuration.git
cd Default-opening-method-configuration
pip install -r requirements.txt
python main.py
```

## Build a single-file `.exe`

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name DefaultOpener --clean --noconfirm main.py
# -> dist/DefaultOpener.exe
```

## Run the smoke tests

```bash
python tests/test_smoke.py
```

## How it works (short version)

Windows resolves file associations through `HKEY_CLASSES_ROOT`, a merged view of
`HKCU\Software\Classes` and `HKLM\Software\Classes`. Per-user entries take
precedence, so the tool writes everything under `HKCU` and reads from the
merged view (`HKEY_CLASSES_ROOT`). Switching a preset rewrites the
`HKCU\Software\Classes\.<ext>` default ProgID and the ProgID's
`shell\open\command` — takes effect immediately, no sign-out required.

## License

[MIT](LICENSE)
