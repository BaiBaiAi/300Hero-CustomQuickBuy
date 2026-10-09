"""JMP fixture tests: only the normal data path may receive the bootstrap."""
from __future__ import annotations

import hashlib
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from sys import path as python_path

python_path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap  # noqa: E402


def make_pack(path: Path, resource_path: bytes, source: bytes) -> None:
    packed = zlib.compress(source, 9)
    header = bytearray(bootstrap.HEADER_SIZE)
    header[:7] = b"DATA1.0"
    struct.pack_into("<I", header, 50, 1)
    record = bytearray(bootstrap.RECORD_SIZE)
    record[:len(resource_path)] = resource_path
    offset = bootstrap.HEADER_SIZE + bootstrap.RECORD_SIZE
    struct.pack_into("<III", record, bootstrap.PATH_BYTES,
                     offset, len(packed), len(source))
    record[bootstrap.PATH_BYTES + 12:] = hashlib.md5(source).hexdigest().encode()
    path.write_bytes(header + record + packed)


class BootstrapTests(unittest.TestCase):
    def test_dynamic_pack_selection_excludes_pve_and_tiyan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            comments = b"".join((b"-- fixture comment %04d\r\n" % i) for i in range(100))
            source = (comments + b"function InitSetup_UI(wnd,bisopen)\r\n"
                      b"    InitMain_Setup(g_setup_ui)\r\nend\r\n")
            make_pack(root / "Data1.jmp", b"..\\pve\\data\\script\\gamehall\\setup\\setup.lua", source)
            make_pack(root / "Data2.jmp", b"..\\tiyan\\data\\script\\gamehall\\setup\\setup.lua", source)
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.locate(root)
            make_pack(root / "Data8.jmp", bootstrap.RESOURCE, source)
            selected, before, after = bootstrap.plan(root)
            self.assertEqual(selected.pack.name, "Data8.jmp")
            self.assertIn(bootstrap.MARKER, after)
            self.assertEqual(before, source)
            backup_dir = root / "backup"
            self.assertIn("installed", bootstrap.install(root, backup_dir))
            self.assertEqual(bootstrap.install(root, backup_dir), "already installed")
            self.assertIn(bootstrap.MARKER, bootstrap.read_resource(bootstrap.locate(root)))
            bootstrap.restore(backup_dir / "setup_jmp.json")
            self.assertEqual(bootstrap.read_resource(bootstrap.locate(root)), source)

    def test_unknown_md5_with_same_anchor_is_supported(self) -> None:
        source = (b"-- client update\r\n" * 80 +
                  b"function InitSetup_UI(wnd,bisopen)\r\n"
                  b"    InitMain_Setup(g_setup_ui)\r\nend\r\n")
        self.assertNotEqual(hashlib.md5(source).hexdigest(), "587b12938b3227586c339963eeb0bcc8")
        self.assertIn(bootstrap.MARKER, bootstrap.patch_source(source))
        with self.assertRaisesRegex(bootstrap.BootstrapError, "anchor"):
            bootstrap.patch_source(b"function Other()\r\nend\r\n")


if __name__ == "__main__":
    unittest.main()
