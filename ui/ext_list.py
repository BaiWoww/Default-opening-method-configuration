"""Left panel: searchable list of file extensions with current default."""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core import registry


class ExtListPanel(QWidget):
    """Shows all known extensions. Emits `ext_selected(ext)` on click."""

    ext_selected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._all_items: List[Dict[str, str]] = []  # [{ext, default_label}]
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 4, 8)

        header = QLabel("文件类型")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("搜索:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入 .py .txt 等")
        self.search_edit.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search_edit, 1)
        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, 1)

        self.count_label = QLabel("共 0 项")
        self.count_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.count_label)

    def refresh(self) -> None:
        """Re-scan HKCU for current associations, then merge with user configs."""
        sys_exts = registry.list_extensions_with_defaults()

        items: List[Dict[str, str]] = []
        for ext, progid in sorted(sys_exts.items()):
            exe = registry.extract_exe_path(registry.get_progid_command(progid) or "")
            label = exe if exe else progid
            items.append({"ext": ext, "default_label": label, "custom": False})

        self._all_items = items
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
        # If not in list (extension just associated), add it
        else:
            self._all_items.append({"ext": ext, "default_label": default_label, "custom": False})
        self._apply_filter(self.search_edit.text())

    def select_ext(self, ext: str) -> None:
        ext = ext.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == ext:
                self.list_widget.setCurrentItem(item)
                return

    def _apply_filter(self, text: str) -> None:
        text = (text or "").strip().lower()
        self.list_widget.clear()
        matched = 0
        for it in self._all_items:
            if text and text not in it["ext"] and text not in it["default_label"].lower():
                continue
            label = it["default_label"]
            # truncate long paths
            if len(label) > 48:
                label = "…" + label[-47:]
            display = f"{it['ext']:<8}  {label}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, it["ext"])
            if it.get("custom"):
                item.setForeground(Qt.darkMagenta)
            self.list_widget.addItem(item)
            matched += 1
        self.count_label.setText(f"共 {matched} 项")

    def _on_selection_changed(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            ext = item.data(Qt.UserRole)
            self.ext_selected.emit(ext)
