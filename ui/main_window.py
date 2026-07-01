"""Main window tying together the extension list and preset panel."""
from __future__ import annotations

import os
import sys
from typing import Dict

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from core import config, registry
from core.models import ExtensionConfig, Preset
from ui.add_ext_dialog import AddExtDialog
from ui.ext_list import ExtListPanel
from ui.preset_panel import PresetPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("默认打开方式管理器")
        self.resize(1000, 640)
        self.setAcceptDrops(True)  # B1

        self._configs: Dict[str, ExtensionConfig] = config.load_all()
        self._build_ui()
        self._install_shortcuts()
        self._restore_geometry()
        self._refresh_all()

    def _build_ui(self) -> None:
        # Central splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("mainSplitter")
        self.ext_panel = ExtListPanel()
        self.preset_panel = PresetPanel()
        self.preset_panel.set_configs(self._configs)

        splitter.addWidget(self.ext_panel)
        splitter.addWidget(self.preset_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([340, 660])
        self.setCentralWidget(splitter)

        self.ext_panel.ext_selected.connect(self.preset_panel.show_extension)
        self.ext_panel.request_add_ext.connect(self._on_add_ext_prefilled)
        self.ext_panel.request_restore.connect(self._on_restore_from_list)
        self.preset_panel.presets_changed.connect(self._on_presets_changed)
        self.preset_panel.default_changed.connect(self._on_default_changed)
        self.preset_panel.status_message.connect(self._show_status)

        # Toolbar
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_refresh = QAction("刷新系统列表", self)
        self.act_refresh.triggered.connect(self._refresh_all)
        tb.addAction(self.act_refresh)

        self.act_add_ext = QAction("+ 新建文件类型", self)
        self.act_add_ext.triggered.connect(self._on_add_ext)
        tb.addAction(self.act_add_ext)

        tb.addSeparator()

        self.act_save = QAction("保存配置", self)
        self.act_save.triggered.connect(self._on_save)
        tb.addAction(self.act_save)

        self.act_about = QAction("关于", self)
        self.act_about.triggered.connect(self._on_about)
        tb.addAction(self.act_about)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪")

    def _install_shortcuts(self) -> None:
        # A7: global keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+F"), self, self.ext_panel.focus_search)
        QShortcut(QKeySequence("Ctrl+N"), self, self._on_add_ext)
        QShortcut(QKeySequence("Ctrl+S"), self, self._on_save)
        QShortcut(QKeySequence("F5"), self, self._refresh_all)
        QShortcut(QKeySequence("Escape"), self.ext_panel.search_edit,
                  self.ext_panel.clear_search)

    # ---- geometry persistence (A5) ----

    def _restore_geometry(self) -> None:
        s = config.load_settings().get("window", {})
        if not isinstance(s, dict):
            return
        if s.get("w") and s.get("h"):
            self.resize(int(s["w"]), int(s["h"]))
        if "x" in s and "y" in s and s["x"] is not None:
            self.move(int(s["x"]), int(s["y"]))
        sizes = s.get("splitter")
        if isinstance(sizes, list) and len(sizes) == 2:
            sp = self.findChild(QSplitter, "mainSplitter")
            if sp:
                sp.setSizes([int(sizes[0]), int(sizes[1])])

    def _save_geometry(self) -> None:
        sp = self.findChild(QSplitter, "mainSplitter")
        sizes = sp.sizes() if sp else [340, 660]
        config.update_settings(
            {
                "window": {
                    "x": self.x(),
                    "y": self.y(),
                    "w": self.width(),
                    "h": self.height(),
                    "splitter": [sizes[0], sizes[1]],
                }
            }
        )

    # ---- refresh / data sync ----

    def _refresh_all(self) -> None:
        self.ext_panel.refresh()
        self._sync_preset_counts()
        for ext, cfg in self._configs.items():
            if cfg.custom:
                progid, cmd, exe = registry.get_current_default(ext)
                label = exe or "(未关联)"
                self.ext_panel.upsert_custom(ext, label)
        self.statusBar().showMessage("已从系统读取默认关联", 4000)

    def _sync_preset_counts(self) -> None:
        counts = {ext: len(cfg.presets) for ext, cfg in self._configs.items()}
        self.ext_panel.set_preset_counts(counts)

    def _show_status(self, msg: str, duration: int) -> None:
        self.statusBar().showMessage(msg, duration)

    # ---- add custom extension ----

    def _on_add_ext(self) -> None:
        dlg = AddExtDialog(self)
        if dlg.exec_() != dlg.Accepted:
            return
        ext, desc, path = dlg.values()
        self._apply_add_ext(ext, desc, path)

    def _on_add_ext_prefilled(self, ext: str) -> None:
        """Add-ext triggered from the left panel / drag-drop with a known ext."""
        dlg = AddExtDialog(self)
        dlg.ext_edit.setText(ext)
        if dlg.exec_() != dlg.Accepted:
            return
        ext, desc, path = dlg.values()
        self._apply_add_ext(ext, desc, path)

    def _apply_add_ext(self, ext: str, desc: str, path: str) -> None:
        cfg = self._configs.get(ext) or ExtensionConfig(ext=ext, custom=True)
        cfg.custom = True
        if desc:
            cfg.description = desc
        if not any(p.path.lower() == path.lower() for p in cfg.presets):
            display_name = os.path.splitext(os.path.basename(path))[0] or "默认程序"
            cfg.presets.append(Preset(name=display_name, path=path, args=""))
        self._configs[ext] = cfg
        config.record_recent_program(path)
        if not config.save_all(self._configs):
            QMessageBox.warning(self, "提示", "保存配置失败,稍后重试。")

        progid = registry.progid_for(ext)
        cmd = f'"{path}" "%1"'
        ok = registry.set_association(ext, progid, cmd, desc or f"{ext} file")
        if ok:
            registry.refresh_shell()
        self._sync_preset_counts()
        self.ext_panel.upsert_custom(ext, path)
        self.preset_panel.show_extension(ext)
        self.ext_panel.select_ext(ext)
        self.statusBar().showMessage(
            f"已新建 {ext} 关联 → {os.path.basename(path)}", 5000
        )

    # ---- presets / default change handlers ----

    def _on_presets_changed(self, ext: str) -> None:
        if not config.save_all(self._configs):
            QMessageBox.warning(self, "提示", "保存配置失败,稍后重试。")
        else:
            self.statusBar().showMessage(f"已保存 {ext} 的预设", 3000)
        self._sync_preset_counts()

    def _on_default_changed(self, ext: str, new_path: str) -> None:
        self.ext_panel.update_default_label(ext, new_path)
        self.statusBar().showMessage(f"已将 {ext} 默认程序切换", 4000)

    def _on_restore_from_list(self, ext: str) -> None:
        """Restore triggered from the left panel context menu."""
        if not registry.has_user_override(ext):
            self.statusBar().showMessage(f"{ext} 当前已是系统默认", 3000)
            return
        ans = QMessageBox.question(
            self,
            "恢复系统默认",
            f"将删除 {ext} 的当前用户关联，恢复到 Windows 出厂默认。\n继续?",
        )
        if ans != QMessageBox.Yes:
            return
        removed = registry.remove_user_override(ext)
        if removed:
            registry.refresh_shell()
            self._refresh_all()
            self.preset_panel.show_extension(ext)
            self.statusBar().showMessage(
                f"已恢复 {ext} 的系统默认", 3000
            )

    def _on_save(self) -> None:
        if config.save_all(self._configs):
            self.statusBar().showMessage("配置已保存", 3000)
        else:
            QMessageBox.warning(self, "失败", "保存失败,请检查写入权限。")

    def _on_about(self) -> None:
        QMessageBox.information(
            self,
            "关于",
            "默认打开方式管理器\n\n"
            "· 管理 HKCU 下文件类型关联\n"
            "· 为每种类型配置多个预设并一键切换\n"
            "· 支持自定义未知扩展名\n"
            "· 拖入文件即可快速定位扩展名\n\n"
            f"配置目录:\n{config.app_dir()}",
        )

    # ---- drag & drop (B1) ----

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if not path or not os.path.isfile(path):
            return
        ext = os.path.splitext(path)[1].lower()
        if not ext:
            QMessageBox.information(self, "提示", "该文件没有扩展名，无法定位。")
            return
        # If the extension is already known, just select it
        from core import registry as reg
        sys_exts = reg.list_extensions_with_defaults()
        if ext in sys_exts or ext in self._configs:
            self.ext_panel.select_ext(ext)
            self.statusBar().showMessage(f"已定位到 {ext}", 3000)
        else:
            ans = QMessageBox.question(
                self,
                "未知类型",
                f"检测到未知扩展名 {ext}\n是否立即新建关联？\n\n"
                f"示例文件: {os.path.basename(path)}",
            )
            if ans == QMessageBox.Yes:
                self._on_add_ext_prefilled(ext)

    def closeEvent(self, event) -> None:
        config.save_all(self._configs)
        self._save_geometry()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DefaultOpener")
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
