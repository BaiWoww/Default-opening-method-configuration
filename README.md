# DefaultOpener

> A lightweight Windows GUI for managing **per-user** default file associations and switching between multiple "presets" for each file type — no admin rights required.

[English](#english) · [中文说明](#中文说明)

---

<a name="english"></a>

## English

### Why?

Windows' built-in "Open with" dialog only lets you set **one** default app per file type, and configuring unknown extensions (e.g. `.xyz`) usually means diving into the registry. **DefaultOpener** makes both trivial — and lets you keep *multiple* "presets" (e.g. `VSCode`, `PyCharm`, `Notepad` for `.py`) so you can flip between them with a single click.

### Features

- 📋 Lists **every** associated extension visible to your user (~900+ on a typical Windows install)
- 🎯 Click an extension to see its current default program and a list of presets
- ⚡ One-click switch between presets — change `.py` from VSCode to PyCharm instantly
- ➕ Add new presets per extension (name, exe path, optional CLI args)
- 🆕 Register **unknown** file types (`.xyz`, `.foo`, …) with a custom program
- 🔒 Writes only to `HKEY_CURRENT_USER\Software\Classes` — **no admin required**
- 💾 Preset config persisted to `%APPDATA%\DefaultOpener\config.json`
- 🧪 Smoke tests for the registry + config layers

### Requirements

- Windows 10 / 11
- Python 3.8+ (for running from source)
- No external runtime dependencies for the built `.exe`

### Install (from source)

```bash
git clone https://github.com/BaiWoww/Default-opening-method-configuration.git
cd Default-opening-method-configuration
pip install -r requirements.txt
python main.py
```

### Build a single-file `.exe`

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name DefaultOpener --clean --noconfirm main.py
# -> dist/DefaultOpener.exe
```

### Run the smoke tests

```bash
python tests/test_smoke.py
```

### How it works (short version)

Windows resolves file associations through `HKEY_CLASSES_ROOT`, a merged view of
`HKCU\Software\Classes` and `HKLM\Software\Classes`. Per-user entries take
precedence, so the tool writes everything under `HKCU` and reads from the
merged view (`HKEY_CLASSES_ROOT`). Switching a preset rewrites the
`HKCU\Software\Classes\.<ext>` default ProgID and the ProgID's
`shell\open\command` — takes effect immediately, no sign-out required.

### License

[MIT](LICENSE)

---

<a name="中文说明"></a>

<details>
<summary><strong>中文说明（点击展开）</strong></summary>

### 项目简介

Windows 自带的「打开方式」对话框只能为每种文件类型设置**一个**默认程序，遇到未注册过的扩展名（`.xyz`）通常要手动改注册表。**DefaultOpener** 让这两件事都变得简单，并支持为每种类型保存**多个预设**（例如 `.py` 的 `VSCode` / `PyCharm` / `记事本`），一键切换。

### 特性

- 📋 列出当前用户可见的全部已关联扩展名（典型 Windows 安装约 900+）
- 🎯 点击扩展名即可查看当前默认程序与预设列表
- ⚡ 一键切换预设（例如把 `.py` 从 VSCode 切到 PyCharm 立即生效）
- ➕ 为每个扩展名添加新预设（名称、程序路径、可选参数）
- 🆕 注册**未知**文件类型（`.xyz`、`.foo` …）并指定打开程序
- 🔒 全部写入 `HKEY_CURRENT_USER\Software\Classes`——**无需管理员**
- 💾 预设配置存于 `%APPDATA%\DefaultOpener\config.json`
- 🧪 提供注册表与配置层的冒烟测试

### 环境要求

- Windows 10 / 11
- Python 3.8+（源码运行需要；`.exe` 直接运行无依赖）

### 从源码运行

```bash
git clone https://github.com/BaiWoww/Default-opening-method-configuration.git
cd Default-opening-method-configuration
pip install -r requirements.txt
python main.py
```

### 打包为单文件 exe

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name DefaultOpener --clean --noconfirm main.py
# 产物：dist/DefaultOpener.exe
```

### 运行测试

```bash
python tests/test_smoke.py
```

### 工作原理（简述）

Windows 通过 `HKEY_CLASSES_ROOT` 解析文件关联——它是 `HKCU\Software\Classes` 与 `HKLM\Software\Classes` 的合并视图，且 HKCU 优先。本工具将所有写入操作落在 `HKCU`，读取走合并视图。切换预设时改写 `HKCU\Software\Classes\.<ext>` 的默认 ProgID 与对应 ProgID 的 `shell\open\command`——立即生效，无需注销或重启资源管理器。

### 许可证

[MIT](LICENSE)

</details>
