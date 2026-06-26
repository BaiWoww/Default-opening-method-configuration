"""Smoke test for the core registry/config logic.

Runs without a GUI. Verifies:
1. set_association writes keys that round-trip
2. list_extensions sees the new association
3. config load/save round-trip works

Note: this test creates a real (but harmless) `.smoketest` association in
the current user's registry. It is cleaned up at the end.
"""
import os
import sys
import tempfile
import winreg

# Ensure project root is on sys.path regardless of where this is run from
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core import config, models, registry  # noqa: E402

TEST_EXT = ".smoketest"
TEST_PROGID = registry.progid_for(TEST_EXT)
TEST_CMD = '"C:\\Windows\\System32\\notepad.exe" "%1"'


def _cleanup_registry():
    """Recursively delete the test ProgID and extension keys from HKCU."""
    def del_tree(root, path):
        try:
            with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
                subs = []
                i = 0
                while True:
                    try:
                        subs.append(winreg.EnumKey(k, i))
                    except OSError:
                        break
                    i += 1
            for s in subs:
                del_tree(root, path + "\\" + s)
            winreg.DeleteKey(root, path)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    HKCU = winreg.HKEY_CURRENT_USER
    del_tree(HKCU, rf"Software\Classes\{TEST_EXT}")
    del_tree(HKCU, rf"Software\Classes\{TEST_PROGID}")


def test_set_and_read():
    ok = registry.set_association(TEST_EXT, TEST_PROGID, TEST_CMD, "Smoke Test")
    assert ok, "set_association returned False"
    exts = registry.list_extensions_with_defaults()
    assert TEST_EXT in exts, f"{TEST_EXT} not in {exts}"
    assert exts[TEST_EXT] == TEST_PROGID
    got_cmd = registry.get_progid_command(TEST_PROGID)
    assert got_cmd == TEST_CMD, f"command mismatch: {got_cmd}"
    _, _, exe = registry.get_current_default(TEST_EXT)
    assert exe and exe.lower().endswith("notepad.exe"), exe
    print("[OK] set + read registry")


def test_config_roundtrip():
    tmpdir = tempfile.mkdtemp()
    saved_dir = os.environ.get("APPDATA", "")
    os.environ["APPDATA"] = tmpdir
    try:
        cfg = models.ExtensionConfig(
            ext=".x",
            presets=[models.Preset(name="A", path="C:\\a.exe")],
            custom=True,
        )
        data = {".x": cfg}
        assert config.save_all(data)
        loaded = config.load_all()
        assert ".x" in loaded
        assert loaded[".x"].presets[0].name == "A"
        assert loaded[".x"].custom is True
    finally:
        os.environ["APPDATA"] = saved_dir
    print("[OK] config roundtrip")


if __name__ == "__main__":
    try:
        test_set_and_read()
        test_config_roundtrip()
        print("ALL TESTS PASSED")
    finally:
        _cleanup_registry()
