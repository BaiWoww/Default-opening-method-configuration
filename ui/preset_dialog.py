"""Dialog for adding or editing a preset (name + path + optional args)."""
from __future__ import annotations

import os
from typing import Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.models import Preset


class PresetDialog(QDialog):
    """Collect preset name, exe path, and optional arguments."""

    def __init__(self, parent: Optional[QWidget] = None, preset: Optional[Preset] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑预设" if preset else "添加预设")
        self.setMinimumWidth(440)
        self._preset = preset
        self._build_ui()
        if preset:
            self.name_edit.setText(preset.name)
            self.path_edit.setText(preset.path)
            self.args_edit.setText(preset.args)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如:VSCode / PyCharm / 记事本")
        form.addRow("名称:", self.name_edit)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("程序完整路径")
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        form.addRow("程序路径:", path_row)

        self.args_edit = QLineEdit()
        self.args_edit.setPlaceholderText("可选:附加命令行参数,%1 表示文件路径")
        form.addRow("参数:", self.args_edit)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择可执行程序", "", "可执行程序 (*.exe);;所有文件 (*.*)"
        )
        if path:
            self.path_edit.setText(path)

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入预设名称。")
            return
        if not path:
            QMessageBox.warning(self, "提示", "请选择程序路径。")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", f"程序路径不存在:\n{path}")
            return
        self.accept()

    def values(self) -> Tuple[str, str, str]:
        return (
            self.name_edit.text().strip(),
            self.path_edit.text().strip(),
            self.args_edit.text().strip(),
        )
