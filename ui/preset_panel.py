"""Right panel: shows current default + presets for the selected extension."""
from __future__ import annotations

import os
from typing import Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import registry
from core.models import ExtensionConfig, Preset


class PresetPanel(QWidget):
    """Display the active default and presets for a given extension."""

    presets_changed = pyqtSignal(str)  # emits ext when presets list modified
    default_changed = pyqtSignal(str, str)  # ext, new default label

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_ext: Optional[str] = None
        self._configs: Dict[str, ExtensionConfig] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 8, 8)

        # Header section: current extension + default
        self.ext_label = QLabel("请选择左侧文件类型")
        self.ext_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.ext_label)

        self.custom_badge = QLabel("")
        self.custom_badge.setStyleSheet(
            "color: white; background:#7b1fa2; padding:1px 6px; "
            "border-radius:3px; font-size:11px;"
        )
        self.custom_badge.setVisible(False)
        layout.addWidget(self.custom_badge)

        # Current default group
        cur_group = QGroupBox("当前默认")
        cur_layout = QVBoxLayout(cur_group)
        self.cur_name_label = QLabel("—")
        self.cur_name_label.setStyleSheet("font-weight: bold;")
        self.cur_path_label = QLabel("")
        self.cur_path_label.setWordWrap(True)
        self.cur_path_label.setStyleSheet("color: #444;")
        self.cur_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cur_layout.addWidget(self.cur_name_label)
        cur_layout.addWidget(self.cur_path_label)
        cur_btn_row = QHBoxLayout()
        self.test_btn = QPushButton("测试打开…")
        self.test_btn.clicked.connect(self._on_test)
        self.test_btn.setEnabled(False)
        cur_btn_row.addWidget(self.test_btn)
        cur_btn_row.addStretch(1)
        cur_layout.addLayout(cur_btn_row)
        layout.addWidget(cur_group)

        # Presets group
        pre_group = QGroupBox("预设列表")
        pre_layout = QVBoxLayout(pre_group)

        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self._on_set_default)
        self.preset_list.itemSelectionChanged.connect(self._on_preset_selection_changed)
        pre_layout.addWidget(self.preset_list, 1)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ 添加预设")
        self.add_btn.clicked.connect(self._on_add_preset)
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self._on_edit_preset)
        self.del_btn = QPushButton("删除")
        self.del_btn.clicked.connect(self._on_del_preset)
        self.set_default_btn = QPushButton("设为默认")
        self.set_default_btn.setStyleSheet("font-weight: bold;")
        self.set_default_btn.clicked.connect(self._on_set_default)
        for b in (self.add_btn, self.edit_btn, self.del_btn, self.set_default_btn):
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        pre_layout.addLayout(btn_row)

        layout.addWidget(pre_group, 1)

        self._set_actions_enabled(False)

    def set_configs(self, configs: Dict[str, ExtensionConfig]) -> None:
        self._configs = configs

    def show_extension(self, ext: str) -> None:
        self._current_ext = ext.lower()
        ext = self._current_ext
        self.ext_label.setText(ext)
        cfg = self._configs.get(ext)
        self.custom_badge.setVisible(bool(cfg and cfg.custom))
        self.custom_badge.setText("自定义类型" if cfg and cfg.custom else "")

        # Current default
        progid, cmd, exe = registry.get_current_default(ext)
        if cmd:
            name = os.path.basename(exe) if exe else progid or "(未知)"
            self.cur_name_label.setText(name)
            self.cur_path_label.setText(cmd)
            self.test_btn.setEnabled(True)
        else:
            self.cur_name_label.setText("(未关联)")
            self.cur_path_label.setText("尚未设置默认打开方式")
            self.test_btn.setEnabled(False)

        # Presets
        self.preset_list.clear()
        if cfg:
            for p in cfg.presets:
                self._append_preset_item(p)
        self._set_actions_enabled(True)

    def _append_preset_item(self, preset: Preset) -> None:
        display = f"{preset.name}\n    {preset.path}"
        if preset.args:
            display += f"  {preset.args}"
        item = QListWidgetItem(display)
        item.setData(Qt.UserRole, preset.name)
        # Check if currently default
        progid, cmd, exe = registry.get_current_default(self._current_ext or "")
        if exe and exe.lower() == preset.path.lower():
            f = item.font()
            f.setBold(True)
            item.setFont(f)
            item.setText(display + "   ✓ 当前默认")
        self.preset_list.addItem(item)

    def _on_preset_selection_changed(self) -> None:
        has = self.preset_list.currentItem() is not None
        self.edit_btn.setEnabled(has)
        self.del_btn.setEnabled(has)
        self.set_default_btn.setEnabled(has)

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.add_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)
        self.set_default_btn.setEnabled(False)

    def _on_add_preset(self) -> None:
        if not self._current_ext:
            return
        from ui.preset_dialog import PresetDialog

        dlg = PresetDialog(self)
        if dlg.exec_() != dlg.Accepted:
            return
        name, path, args = dlg.values()
        cfg = self._configs.setdefault(self._current_ext, ExtensionConfig(ext=self._current_ext))
        # Replace if same name exists
        for p in cfg.presets:
            if p.name == name:
                p.path = path
                p.args = args
                break
        else:
            cfg.presets.append(Preset(name=name, path=path, args=args))
        self.presets_changed.emit(self._current_ext)
        self.show_extension(self._current_ext)

    def _on_edit_preset(self) -> None:
        if not self._current_ext:
            return
        item = self.preset_list.currentItem()
        if not item:
            return
        old_name = item.data(Qt.UserRole)
        cfg = self._configs.get(self._current_ext)
        if not cfg:
            return
        idx = next((i for i, p in enumerate(cfg.presets) if p.name == old_name), None)
        if idx is None:
            return
        from ui.preset_dialog import PresetDialog

        dlg = PresetDialog(self, preset=cfg.presets[idx])
        if dlg.exec_() != dlg.Accepted:
            return
        name, path, args = dlg.values()
        cfg.presets[idx] = Preset(name=name, path=path, args=args)
        self.presets_changed.emit(self._current_ext)
        self.show_extension(self._current_ext)

    def _on_del_preset(self) -> None:
        if not self._current_ext:
            return
        item = self.preset_list.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        cfg = self._configs.get(self._current_ext)
        if not cfg:
            return
        ans = QMessageBox.question(self, "确认", f"删除预设「{name}」?")
        if ans != QMessageBox.Yes:
            return
        cfg.presets = [p for p in cfg.presets if p.name != name]
        self.presets_changed.emit(self._current_ext)
        self.show_extension(self._current_ext)

    def _on_set_default(self) -> None:
        if not self._current_ext:
            return
        item = self.preset_list.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        cfg = self._configs.get(self._current_ext)
        if not cfg:
            return
        preset = next((p for p in cfg.presets if p.name == name), None)
        if not preset:
            return
        progid = registry.progid_for(self._current_ext)
        cmd = preset.command_line()
        friendly = cfg.description or f"{self._current_ext} file"
        ok = registry.set_association(self._current_ext, progid, cmd, friendly)
        if ok:
            registry.refresh_shell()
            self.default_changed.emit(self._current_ext, preset.path)
            self.show_extension(self._current_ext)
            QMessageBox.information(self, "完成", f"已将 {self._current_ext} 的默认程序切换为:\n{preset.name}")
        else:
            QMessageBox.critical(self, "失败", "写入注册表失败,请检查权限。")

    def _on_test(self) -> None:
        if not self._current_ext:
            return
        # Pick any existing file with this extension; if none, create a temp one
        target = self._find_sample_file(self._current_ext)
        if not target:
            # create a small temp file with this extension
            import tempfile

            fd, target = tempfile.mkstemp(suffix=self._current_ext)
            os.close(fd)
            created = True
        else:
            created = False
        try:
            os.startfile(target)  # noqa
        except Exception as e:
            QMessageBox.critical(self, "失败", f"无法用默认程序打开:\n{e}")
        finally:
            if created:
                try:
                    os.unlink(target)
                except OSError:
                    pass

    def _find_sample_file(self, ext: str) -> Optional[str]:
        ext = ext.lower()
        for root_dir in (
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~"),
        ):
            if not os.path.isdir(root_dir):
                continue
            try:
                for name in os.listdir(root_dir):
                    if name.lower().endswith(ext):
                        p = os.path.join(root_dir, name)
                        if os.path.isfile(p):
                            return p
            except OSError:
                continue
        return None
