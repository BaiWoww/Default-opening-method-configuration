"""Dialog for adding a new (custom) file extension association."""
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

from core import registry


class AddExtDialog(QDialog):
    """Collect extension, description, and initial exe path."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建文件类型")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.ext_edit = QLineEdit()
        self.ext_edit.setPlaceholderText(".xyz")
        form.addRow("扩展名:", self.ext_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("例如:XYZ 工程文件")
        form.addRow("描述:", self.desc_edit)

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("用于打开该类型文件的程序")
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        form.addRow("默认程序:", path_row)

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
        ext = self.ext_edit.text().strip().lower()
        if not ext:
            QMessageBox.warning(self, "提示", "请输入扩展名。")
            return
        if not ext.startswith("."):
            ext = "." + ext
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请选择默认程序。")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", f"程序路径不存在:\n{path}")
            return
        if not path.lower().endswith(".exe"):
            ans = QMessageBox.question(
                self,
                "确认",
                f"所选文件不是 .exe，是否仍要使用?\n{path}",
            )
            if ans != QMessageBox.Yes:
                return
        self.ext_edit.setText(ext)
        self.accept()

    def values(self) -> Tuple[str, str, str]:
        return (
            self.ext_edit.text().strip().lower(),
            self.desc_edit.text().strip(),
            self.path_edit.text().strip(),
        )
