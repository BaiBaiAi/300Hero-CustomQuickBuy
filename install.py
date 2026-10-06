"""Install the independent quick-buy entry into an already bootstrapped 300Hero."""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Install 300Hero custom quick buy")
    parser.add_argument("game_dir", type=Path, help="300Hero root directory")
    args = parser.parse_args()
    game = args.game_dir.resolve()
    if not game.is_dir():
        parser.error(f"Game directory does not exist: {game}")
    target = game / "external_lua"
    target.mkdir(exist_ok=True)
    source = Path(__file__).resolve().parent / "external_lua"
    old_entry = target / "entry.lua"
    if old_entry.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = target / f"entry.before_custom_quickbuy.{stamp}.lua"
        shutil.copy2(old_entry, backup)
        print(f"Previous entry backed up: {backup}")
    shutil.copy2(source / "entry.lua", old_entry)
    addon = target / "custom_quickbuy"
    addon.mkdir(exist_ok=True)
    (addon / "heroes").mkdir(exist_ok=True)
    script = (source / "custom_quickbuy" / "quickbuy.lua").read_text(encoding="utf-8")
    (addon / "quickbuy.lua").write_bytes(script.encode("gbk"))
    shutil.copy2(source / "custom_quickbuy" / "dark.bmp", addon / "dark.bmp")
    print(f"Installed to: {target}")
    print("Close the game before installation; restart it to load the new entry.")


if __name__ == "__main__":
    main()
