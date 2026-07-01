"""Left panel: searchable, filterable list of file extensions with badges."""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core import registry


class ExtListPanel(QWidget):
    """Shows all known extensions. Emits `ext_selected(ext)` on click."""

    ext_selected = pyqtSignal(str)
    request_add_ext = pyqtSignal(str)  # ext to prefill in add-dialog
    request_restore = pyqtSignal(str)  # ext to restore system default

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._all_items: List[Dict[str, object]] = []
        self._preset_counts: Dict[str, int] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 4, 8)

        header = QLabel("文件类型")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        # Filter toggles (A3)
        filter_row = QHBoxLayout()
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)
        self.btn_all = QPushButton("全部")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_presets = QPushButton("有预设")
        self.btn_presets.setCheckable(True)
        self.btn_custom = QPushButton("自定义")
        self.btn_custom.setCheckable(True)
        for b in (self.btn_all, self.btn_presets, self.btn_custom):
            self.filter_group.addButton(b)
            b.clicked.connect(self._apply_filter)
            filter_row.addWidget(b)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入 .py .txt 等")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list_widget, 1)

        self.count_label = QLabel("共 0 项")
        self.count_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.count_label)

    def refresh(self) -> None:
        """Re-scan system for current associations."""
        sys_exts = registry.list_extensions_with_defaults()

        items: List[Dict[str, object]] = []
        for ext, progid in sorted(sys_exts.items()):
            exe = registry.extract_exe_path(registry.get_progid_command(progid) or "")
            label = exe if exe else progid
            items.append(
                {"ext": ext, "default_label": label, "custom": False}
            )

        self._all_items = items
        self._apply_filter(self.search_edit.text())

    def set_preset_counts(self, counts: Dict[str, int]) -> None:
        self._preset_counts = counts
        self._apply_filter(self.search_edit.text())

    def upsert_custom(self, ext: str, default_label: str) -> None:
        ext = ext.lower()
        for it in self._all_items:
            if it["ext"] == ext:
                it["default_label"] = default_label
                it["custom"] = True
                break
        else:
            self._all_items.append(
                {"ext": ext, "default_label": default_label, "custom": True}
            )
        self._apply_filter(self.search_edit.text())

    def update_default_label(self, ext: str, default_label: str) -> None:
        ext = ext.lower()
        for it in self._all_items:
            if it["ext"] == ext:
                it["default_label"] = default_label
                break
        else:
            self._all_items.append(
                {"ext": ext, "default_label": default_label, "custom": False}
            )
        self._apply_filter(self.search_edit.text())

    def select_ext(self, ext: str) -> None:
        ext = ext.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == ext:
                self.list_widget.setCurrentItem(item)
                self.list_widget.scrollToItem(item)
                return

    def focus_search(self) -> None:
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def clear_search(self) -> None:
        self.search_edit.clear()

    def _active_filter(self) -> str:
        btn = self.filter_group.checkedButton()
        if btn is self.btn_presets:
            return "presets"
        if btn is self.btn_custom:
            return "custom"
        return "all"

    def _apply_filter(self, *args) -> None:
        text = self.search_edit.text().strip().lower()
        mode = self._active_filter()
        self.list_widget.clear()
        matched = 0
        for it in self._all_items:
            ext = it["ext"]
            count = self._preset_counts.get(ext, 0)
            is_custom = it.get("custom", False)
            if mode == "presets" and count == 0:
                continue
            if mode == "custom" and not is_custom:
                continue
            label = it["default_label"]
            if text and text not in ext and text not in label.lower():
                continue
            display = f"{ext:<8}"
            if count > 0:
                display += f"  ●{count}"
            truncated = label
            if len(label) > 48:
                truncated = "…" + label[-47:]
            display += f"  {truncated}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, ext)
            item.setToolTip(f"{ext}\n当前默认: {label}\n预设数: {count}")
            if is_custom:
                item.setForeground(Qt.darkMagenta)
            self.list_widget.addItem(item)
            matched += 1
        self.count_label.setText(f"共 {matched} 项")

    def _on_selection_changed(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            ext = item.data(Qt.UserRole)
            self.ext_selected.emit(ext)

    def _on_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        ext = item.data(Qt.UserRole)
        menu = QMenu(self)
        act_copy = menu.addAction("复制扩展名")
        menu.addSeparator()
        act_find = menu.addAction("在资源管理器中查找示例文件")
        act_restore = menu.addAction("恢复系统默认")
        action = menu.exec_(self.list_widget.viewport().mapToGlobal(pos))
        if action is act_copy:
            cb = self.list_widget.clipboard()
            if cb is None:
                from PyQt5.QtWidgets import QApplication
                cb = QApplication.clipboard()
            cb.setText(ext)
        elif action is act_find:
            self._find_sample_in_explorer(ext)
        elif action is act_restore:
            self.request_restore.emit(ext)

    def _find_sample_in_explorer(self, ext: str) -> None:
        import os
        import subprocess
        import tempfile

        target = None
        created = False
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
                            target = p
                            break
            except OSError:
                continue
            if target:
                break
        if not target:
            fd, target = tempfile.mkstemp(suffix=ext)
            os.close(fd)
            created = True
        try:
            subprocess.Popen(["explorer", "/select,", target])
        except OSError:
            QMessageBox.information(self, "提示", f"示例文件路径:\n{target}")
        finally:
            if created:
                try:
                    os.unlink(target)
                except OSError:
                    pass
