"""Right panel: shows current default + presets for the selected extension."""
from __future__ import annotations

import os
from typing import Dict, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QKeySequence, QPalette
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

from core import registry
from core.models import ExtensionConfig, Preset


class PresetPanel(QWidget):
    """Display the active default and presets for a given extension."""

    presets_changed = pyqtSignal(str)  # emits ext when presets list modified
    default_changed = pyqtSignal(str, str)  # ext, new default label
    status_message = pyqtSignal(str, int)  # message, duration ms

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_ext: Optional[str] = None
        self._configs: Dict[str, ExtensionConfig] = {}
        self._build_ui()
        self._install_shortcuts()

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
        # B2: capture current default as preset
        self.capture_btn = QPushButton("➕ 存为预设")
        self.capture_btn.setToolTip("将当前默认程序保存为预设，免去重新浏览路径")
        self.capture_btn.clicked.connect(self._on_capture_default)
        self.capture_btn.setEnabled(False)
        cur_btn_row.addWidget(self.capture_btn)
        cur_btn_row.addStretch(1)
        cur_layout.addLayout(cur_btn_row)
        layout.addWidget(cur_group)

        # Presets group
        pre_group = QGroupBox("预设列表")
        pre_layout = QVBoxLayout(pre_group)

        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self._on_set_default)
        self.preset_list.itemSelectionChanged.connect(self._on_preset_selection_changed)
        self.preset_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.preset_list.customContextMenuRequested.connect(self._on_context_menu)
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

        # B4: restore system default
        restore_row = QHBoxLayout()
        self.restore_btn = QPushButton("↩ 恢复系统默认")
        self.restore_btn.setToolTip(
            "删除当前用户的关联覆盖，回到 Windows 出厂默认程序"
        )
        self.restore_btn.clicked.connect(self._on_restore_default)
        self.restore_btn.setEnabled(False)
        restore_row.addWidget(self.restore_btn)
        restore_row.addStretch(1)
        pre_layout.addLayout(restore_row)

        layout.addWidget(pre_group, 1)

        self._set_actions_enabled(False)

    def _install_shortcuts(self) -> None:
        # A7: keyboard shortcuts on the preset list
        QShortcut(QKeySequence(Qt.Key_Return), self.preset_list, self._on_set_default)
        QShortcut(QKeySequence(Qt.Key_Enter), self.preset_list, self._on_set_default)
        QShortcut(QKeySequence.Delete, self.preset_list, self._on_del_preset)
        QShortcut(
            QKeySequence(Qt.Key_Escape), self.preset_list, self.preset_list.clearFocus
        )

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
            self.cur_path_label.setToolTip(exe or cmd or "")
            self.test_btn.setEnabled(True)
            self.capture_btn.setEnabled(True)
        else:
            self.cur_name_label.setText("(未关联)")
            self.cur_path_label.setText("尚未设置默认打开方式")
            self.cur_path_label.setToolTip("")
            self.test_btn.setEnabled(False)
            self.capture_btn.setEnabled(False)

        # B4: restore availability
        self.restore_btn.setEnabled(registry.has_user_override(ext))

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
        item.setToolTip(f"{preset.name}\n路径: {preset.path}\n参数: {preset.args or '(无)'}")
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
        cfg = self._configs.setdefault(
            self._current_ext, ExtensionConfig(ext=self._current_ext)
        )
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
            # A1: no modal box; flash the item + status message
            self._flash_item(item)
            self.status_message.emit(
                f"已将 {self._current_ext} 默认程序切换为 {preset.name}", 3000
            )
        else:
            QMessageBox.critical(self, "失败", "写入注册表失败，请检查权限。")

    def _flash_item(self, item: QListWidgetItem) -> None:
        """Briefly highlight an item to confirm the switch (A1)."""
        orig_bg = item.background()
        highlight = QPalette().highlight().color()
        # apply via stylesheet-ish: use setBackground
        from PyQt5.QtGui import QColor
        item.setBackground(QColor("#a5d6a7"))
        QTimer.singleShot(300, lambda: item.setBackground(orig_bg))

    def _on_capture_default(self) -> None:
        """B2: capture the current system default as a preset."""
        if not self._current_ext:
            return
        progid, cmd, exe = registry.get_current_default(self._current_ext)
        if not exe:
            QMessageBox.information(self, "提示", "当前没有默认程序可捕获。")
            return
        name = os.path.splitext(os.path.basename(exe))[0] or "默认程序"
        cfg = self._configs.setdefault(
            self._current_ext, ExtensionConfig(ext=self._current_ext)
        )
        # dedup by path
        for p in cfg.presets:
            if p.path.lower() == exe.lower():
                QMessageBox.information(self, "提示", f"预设「{p.name}」已使用该程序。")
                return
        cfg.presets.append(Preset(name=name, path=exe, args=""))
        self.presets_changed.emit(self._current_ext)
        self.show_extension(self._current_ext)
        self.status_message.emit(f"已捕获当前默认为预设「{name}」", 3000)

    def _on_restore_default(self) -> None:
        """B4: remove the HKCU override so system default returns."""
        if not self._current_ext:
            return
        ans = QMessageBox.question(
            self,
            "恢复系统默认",
            f"将删除 {self._current_ext} 的当前用户关联，恢复到 Windows 出厂默认。\n继续?",
        )
        if ans != QMessageBox.Yes:
            return
        removed = registry.remove_user_override(self._current_ext)
        if removed:
            registry.refresh_shell()
            self.show_extension(self._current_ext)
            self.status_message.emit(
                f"已恢复 {self._current_ext} 的系统默认", 3000
            )
        else:
            self.status_message.emit("当前已是系统默认，无需恢复", 3000)

    def _on_test(self) -> None:
        if not self._current_ext:
            return
        target = self._find_sample_file(self._current_ext)
        if not target:
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

    def _on_context_menu(self, pos) -> None:
        item = self.preset_list.itemAt(pos)
        if not item:
            return
        name = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_set = menu.addAction("设为默认")
        menu.addSeparator()
        act_edit = menu.addAction("编辑")
        act_del = menu.addAction("删除")
        # select the item first so actions target it
        self.preset_list.setCurrentItem(item)
        action = menu.exec_(self.preset_list.viewport().mapToGlobal(pos))
        if action is act_set:
            self._on_set_default()
        elif action is act_edit:
            self._on_edit_preset()
        elif action is act_del:
            self._on_del_preset()

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
