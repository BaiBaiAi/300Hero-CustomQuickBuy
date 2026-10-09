"""Installer and uninstaller round trip on a disposable JMP fixture."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap
import install
from test_bootstrap import make_pack


class InstallTests(unittest.TestCase):
    def test_install_then_uninstall_restores_client_and_earlier_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            game = Path(directory) / "300Hero"
            game.mkdir()
            comments = b"".join((b"-- fixture comment %04d\r\n" % i) for i in range(100))
            source = comments + b"function InitSetup_UI(wnd,bisopen)\r\n    InitMain_Setup(g_setup_ui)\r\nend\r\n"
            make_pack(game / "Data8.jmp", bootstrap.RESOURCE, source)
            old_entry = game / "external_lua" / "entry.lua"
            old_entry.parent.mkdir()
            old_entry.write_bytes(b"-- original game script\n")
            with patch.object(install, "require_closed_game"):
                install.deploy(game)
                self.assertIn(bootstrap.MARKER, bootstrap.read_resource(bootstrap.locate(game)))
                (game / "external_lua/custom_quickbuy/heroes/121.txt").write_text("1=21113\n")
                install.deploy(game)
                archive = install.uninstall(game)
                self.assertIsNotNone(archive)
                self.assertEqual(bootstrap.read_resource(bootstrap.locate(game)), source)
                self.assertEqual(old_entry.read_bytes(), b"-- original game script\n")
                self.assertFalse((game / "external_lua/custom_quickbuy").exists())
                self.assertFalse((game / "custom_quickbuy_backups").exists())
                self.assertEqual((archive / "external_lua/custom_quickbuy/heroes/121.txt").read_text(), "1=21113\n")
                self.assertIsNone(install.uninstall(game))


if __name__ == "__main__":
    unittest.main()
