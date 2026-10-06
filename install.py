"""Install quick-buy files and this project's version-locked JMP bootstrap."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import zlib
from datetime import datetime
from pathlib import Path

import bootstrap


def require_closed_game() -> None:
    if os.name != "nt":
        return
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq 300.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, check=True,
    )
    if any(line.startswith('"300.exe"') for line in result.stdout.splitlines()):
        raise bootstrap.BootstrapError("300.exe is running; close the game before installing or uninstalling")


def deploy(game: Path) -> None:
    require_closed_game()
    # Validate the client and all source files before writing to the game.
    resource, _, _ = bootstrap.plan(game)
    source_dir = Path(__file__).resolve().parent / "external_lua"
    entry_bytes = (source_dir / "entry.lua").read_bytes()
    addon_source = source_dir / "custom_quickbuy"
    lua_bytes = (addon_source / "quickbuy.lua").read_text(encoding="utf-8").encode("gbk")
    image_bytes = (addon_source / "dark.bmp").read_bytes()

    target_dir = game / "external_lua"
    addon_target = target_dir / "custom_quickbuy"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = game / "custom_quickbuy_backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    addon_target.mkdir(parents=True, exist_ok=True)
    (addon_target / "heroes").mkdir(exist_ok=True)

    outputs = {
        target_dir / "entry.lua": entry_bytes,
        addon_target / "quickbuy.lua": lua_bytes,
        addon_target / "dark.bmp": image_bytes,
    }
    originals: dict[Path, Path | None] = {}
    for target in outputs:
        saved = backup_dir / target.name if target.exists() else None
        if saved:
            shutil.copy2(target, saved)
        originals[target] = saved
    try:
        for target, content in outputs.items():
            target.write_bytes(content)
        boot_status = bootstrap.install(game, backup_dir)
        for target, content in outputs.items():
            if target.read_bytes() != content:
                raise bootstrap.BootstrapError(f"File verification failed: {target}")
        if bootstrap.MARKER not in bootstrap.read_resource(bootstrap.locate(game)):
            raise bootstrap.BootstrapError("JMP bootstrap marker missing after installation")
    except Exception:
        for target, saved in originals.items():
            if saved:
                shutil.copy2(saved, target)
            elif target.exists():
                target.unlink()
        raise
    print(f"Client setup.lua: {resource.pack.name} #{resource.index}")
    print(f"Original MD5: {bootstrap.SUPPORTED_MD5}")
    print(f"JMP bootstrap: {boot_status}")
    print(f"Quick-buy files: {addon_target}")
    print(f"Backup directory: {backup_dir}")
    print("Hero configurations and last_hero.txt were preserved.")


def uninstall(game: Path) -> Path | None:
    """Restore the original JMP and move this add-on outside the game folder."""
    require_closed_game()
    entry = game / "external_lua" / "entry.lua"
    addon = game / "external_lua" / "custom_quickbuy"
    resource = bootstrap.locate(game)
    current = bootstrap.read_resource(resource)
    backups = game / "custom_quickbuy_backups"
    owned_entry = entry.exists() and b"__CQB_STARTED" in entry.read_bytes()
    if bootstrap.MARKER in current and entry.exists() and not owned_entry:
        raise bootstrap.BootstrapError("external_lua/entry.lua is not this project's script")
    if bootstrap.MARKER not in current and not owned_entry and not addon.exists() and not backups.exists():
        return None
    candidates = sorted(backups.glob("*/setup_jmp.json"))
    original_backup = None
    for candidate in candidates:
        data = json.loads(candidate.read_text(encoding="utf-8"))
        if Path(data["pack"]).resolve() != resource.pack.resolve():
            continue
        original = zlib.decompress(bytes.fromhex(data["compressed"]))
        if hashlib.md5(original).hexdigest() != data["source_md5"]:
            raise bootstrap.BootstrapError(f"Invalid JMP backup: {candidate}")
        if bootstrap.MARKER in current and bootstrap.patch_source(original) != current:
            continue
        original_backup = candidate
        break

    if bootstrap.MARKER in current:
        if original_backup is None:
            raise bootstrap.BootstrapError("No matching original JMP backup; refusing to overwrite the client")
        bootstrap.restore(original_backup)

    archive = game.parent / f"{game.name}_quickbuy_uninstall" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    archive.mkdir(parents=True, exist_ok=False)
    for source, relative in ((addon, Path("external_lua/custom_quickbuy")),
                             (backups, Path("custom_quickbuy_backups"))):
        if source.exists():
            destination = archive / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
    if owned_entry:
        destination = archive / "external_lua" / "entry.lua"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(entry), str(destination))

    if original_backup is not None:
        first_backup = archive / "custom_quickbuy_backups" / original_backup.parent.name
        for name, destination in (("entry.lua", entry),
                                  ("quickbuy.lua", addon / "quickbuy.lua"),
                                  ("dark.bmp", addon / "dark.bmp")):
            source = first_backup / name
            if source.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    external = game / "external_lua"
    if external.is_dir() and not any(external.iterdir()):
        external.rmdir()
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description="300Hero custom quick-buy installer")
    parser.add_argument("game_dir", type=Path, help="directory containing Data*.jmp")
    parser.add_argument("--status", action="store_true", help="inspect bootstrap without writing")
    parser.add_argument("--uninstall", action="store_true", help="restore JMP and remove this add-on")
    parser.add_argument("--restore-jmp", type=Path, metavar="BACKUP",
                        help="restore setup_jmp.json from a previous installation")
    args = parser.parse_args()
    game = args.game_dir.resolve()
    if not game.is_dir():
        parser.error(f"Game directory does not exist: {game}")
    try:
        if args.status:
            resource = bootstrap.locate(game)
            source = bootstrap.read_resource(resource)
            print(f"{resource.pack.name} #{resource.index}: MD5 "
                  f"{hashlib.md5(source).hexdigest()}, "
                  f"quick-buy bootstrap {'installed' if bootstrap.MARKER in source else 'absent'}")
        elif args.uninstall:
            archive = uninstall(game)
            print(f"Uninstalled; backup: {archive}" if archive else "Already uninstalled")
        elif args.restore_jmp:
            require_closed_game()
            bootstrap.restore(args.restore_jmp.resolve())
            print("JMP bootstrap restored from backup")
        else:
            deploy(game)
    except (OSError, ValueError, bootstrap.BootstrapError) as exc:
        parser.exit(1, f"Installation failed: {exc}\n")


if __name__ == "__main__":
    main()
