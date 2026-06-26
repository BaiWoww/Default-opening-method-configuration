"""Main window tying together the extension list and preset panel."""
from __future__ import annotations

import os
import sys
from typing import Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAction,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from core import config, registry
from core.models import ExtensionConfig
from ui.add_ext_dialog import AddExtDialog
from ui.ext_list import ExtListPanel
from ui.preset_panel import PresetPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("默认打开方式管理器")
        self.resize(1000, 640)

        self._configs: Dict[str, ExtensionConfig] = config.load_all()
        self._build_ui()
        self._refresh_all()

    def _build_ui(self) -> None:
        # Central splitter
        splitter = QSplitter(Qt.Horizontal)
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
        self.preset_panel.presets_changed.connect(self._on_presets_changed)
        self.preset_panel.default_changed.connect(self._on_default_changed)

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

    def _refresh_all(self) -> None:
        self.ext_panel.refresh()
        # Reapply any custom markers from configs (those with custom=True)
        for ext, cfg in self._configs.items():
            if cfg.custom:
                # ensure visible even if not in HKCU list yet
                progid, cmd, exe = registry.get_current_default(ext)
                label = exe or "(未关联)"
                self.ext_panel.upsert_custom(ext, label)
        self.statusBar().showMessage("已从系统读取默认关联", 4000)

    def _on_add_ext(self) -> None:
        dlg = AddExtDialog(self)
        if dlg.exec_() != dlg.Accepted:
            return
        ext, desc, path = dlg.values()
        # Save into config
        cfg = self._configs.get(ext) or ExtensionConfig(ext=ext, custom=True)
        cfg.custom = True
        if desc:
            cfg.description = desc
        # Always add a preset for the chosen default program
        from core.models import Preset

        if not any(p.path.lower() == path.lower() for p in cfg.presets):
            display_name = os.path.splitext(os.path.basename(path))[0] or "默认程序"
            cfg.presets.append(Preset(name=display_name, path=path, args=""))
        self._configs[ext] = cfg
        if not config.save_all(self._configs):
            QMessageBox.warning(self, "提示", "保存配置失败,稍后重试。")

        # Write registry
        progid = registry.progid_for(ext)
        cmd = f'"{path}" "%1"'
        ok = registry.set_association(ext, progid, cmd, desc or f"{ext} file")
        if ok:
            registry.refresh_shell()
        self.ext_panel.upsert_custom(ext, path)
        self.preset_panel.show_extension(ext)
        self.ext_panel.select_ext(ext)
        self.statusBar().showMessage(f"已新建 {ext} 关联 → {os.path.basename(path)}", 5000)

    def _on_presets_changed(self, ext: str) -> None:
        # cfg already mutated inside panel; just persist
        if not config.save_all(self._configs):
            QMessageBox.warning(self, "提示", "保存配置失败,稍后重试。")
        else:
            self.statusBar().showMessage(f"已保存 {ext} 的预设", 3000)

    def _on_default_changed(self, ext: str, new_path: str) -> None:
        # Refresh left list label for this extension
        self.ext_panel.update_default_label(ext, new_path)
        self.statusBar().showMessage(f"已将 {ext} 默认程序切换", 4000)

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
            "· 支持自定义未知扩展名\n\n"
            f"配置目录:\n{config.app_dir()}",
        )

    def closeEvent(self, event) -> None:
        # auto-save on exit
        config.save_all(self._configs)
        super().closeEvent(event)


def main() -> int:
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("DefaultOpener")
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
