"""Build the Windows installer EXE with the bundled Lua sources and assets."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
subprocess.run(
    [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed", "--name", "300Hero-QuickBuy-Installer-20261007",
        "--add-data", f"{ROOT / 'external_lua'}{';' if sys.platform == 'win32' else ':'}external_lua",
        "--add-data", f"{ROOT / 'LICENSE'}{';' if sys.platform == 'win32' else ':'}.",
        str(ROOT / "quickbuy_installer.py"),
    ],
    cwd=ROOT,
    check=True,
)
