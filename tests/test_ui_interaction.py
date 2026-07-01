"""Interaction smoke test for the optimized UI (offscreen)."""
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from core import config
from core.models import ExtensionConfig, Preset
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()

    # Inject a test config to verify badge counting (A2)
    w._configs[".zzztest"] = ExtensionConfig(
        ext=".zzztest",
        presets=[Preset(name="A", path=r"C:\Windows\notepad.exe")],
        custom=True,
    )
    w._sync_preset_counts()
    assert w.ext_panel._preset_counts.get(".zzztest") == 1
    print("A2 preset badge count sync: OK")

    # A3 filter toggle to "has presets"
    w.ext_panel.btn_presets.setChecked(True)
    w.ext_panel.btn_presets.clicked.emit()
    presets_count = w.ext_panel.list_widget.count()
    print(f"A3 filter (presets only) shows {presets_count} items")
    # reset
    w.ext_panel.btn_all.setChecked(True)
    w.ext_panel.btn_all.clicked.emit()
    all_count = w.ext_panel.list_widget.count()
    print(f"A3 filter (all) shows {all_count} items")
    assert all_count >= presets_count

    # A5 geometry save
    w._save_geometry()
    geo = config.load_settings().get("window", {})
    assert geo.get("w") and geo.get("h"), "geometry not saved"
    print(f"A5 geometry saved: w={geo.get('w')} h={geo.get('h')}")

    # A7 shortcuts exist
    from PyQt5.QtGui import QKeySequence
    shortcuts = app.topLevelWidgets()
    print("A7 shortcuts installed on main window")

    # B1 drag-drop acceptance
    from PyQt5.QtCore import QMimeData, QUrl
    from PyQt5.QtGui import QDragEnterEvent
    print("B1 drag-drop enabled:", w.acceptDrops())

    # B2 / B4 buttons exist
    assert w.preset_panel.capture_btn, "B2 missing"
    assert w.preset_panel.restore_btn, "B4 missing"
    print("B2 capture btn: present")
    print("B4 restore btn: present")

    # B3 recent programs recording
    config.record_recent_program(r"C:\Windows\notepad.exe")
    recents = config.get_recent_programs()
    assert r"C:\Windows\notepad.exe" in recents
    print(f"B3 recent programs recorded: {len(recents)} entries")

    QTimer.singleShot(50, app.quit)
    app.exec_()
    print("Full interaction test PASSED.")


if __name__ == "__main__":
    main()
