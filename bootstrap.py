"""300Hero JMP bootstrap for the standalone quick-buy project.

Only the setup.lua resource is changed. The original index record and compressed
bytes are saved before writing so this patch can be restored without a full pack.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HEADER_SIZE = 54
RECORD_SIZE = 304
PATH_BYTES = 260
RESOURCE = b"..\\data\\script\\gamehall\\setup\\setup.lua"
MARKER = b"--CQB-BOOT"
LOAD_LINE = b"    InitMain_Setup(g_setup_ui)\r\n"
HOOK = (
    b"    --CQB-BOOT\r\n"
    b'    local f=loadfile("external_lua/entry.lua")\r\n'
    b"    if f then pcall(f) end\r\n"
)


class BootstrapError(RuntimeError):
    pass


@dataclass(frozen=True)
class Resource:
    pack: Path
    index: int
    record_offset: int
    data_offset: int
    compressed_size: int
    raw_size: int
    digest: str


def _valid_nonstandard_index(stream, count: int, length: int) -> bool:
    """Accept an unusual header only when its entire JMP index and samples verify."""
    if not 0 < count <= 1_000_000:
        return False
    index_end = HEADER_SIZE + count * RECORD_SIZE
    if index_end > length:
        return False
    samples = {0, count // 2, count - 1}
    sample_records = []
    stream.seek(HEADER_SIZE)
    for index in range(count):
        record = stream.read(RECORD_SIZE)
        path = record[:PATH_BYTES].split(b"\0", 1)[0]
        offset, packed, raw = struct.unpack_from("<III", record, PATH_BYTES)
        digest = record[PATH_BYTES + 12:]
        if (not path.replace(b"/", b"\\").startswith(b"..\\")
                or packed == 0 or offset < index_end or offset + packed > length
                or len(digest) != 32
                or any(char not in b"0123456789abcdefABCDEF" for char in digest)):
            return False
        if index in samples:
            sample_records.append((offset, packed, raw, digest.lower()))
    for offset, packed, raw, digest in sample_records:
        stream.seek(offset)
        try:
            source = zlib.decompress(stream.read(packed))
        except zlib.error:
            return False
        if len(source) != raw or hashlib.md5(source).hexdigest().encode("ascii") != digest:
            return False
    return True


def locate(game: Path) -> Resource:
    matches: list[Resource] = []
    packs = sorted(path for path in game.iterdir()
                   if path.is_file() and path.suffix.lower() == ".jmp")
    if not packs:
        raise BootstrapError(f"No JMP files found in game directory: {game}")
    for pack in packs:
        length = pack.stat().st_size
        if length < HEADER_SIZE:
            continue
        with pack.open("rb") as stream:
            header = stream.read(HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                continue
            count = struct.unpack_from("<I", header, 50)[0]
            if HEADER_SIZE + count * RECORD_SIZE > length:
                if header.startswith((b"DATA1.0", b"DATA2.0")):
                    raise BootstrapError(f"Invalid JMP index size: {pack}")
                continue
            if not header.startswith((b"DATA1.0", b"DATA2.0")):
                if not _valid_nonstandard_index(stream, count, length):
                    continue
                stream.seek(HEADER_SIZE)
            for index in range(count):
                record = stream.read(RECORD_SIZE)
                path = record[:PATH_BYTES].split(b"\0", 1)[0]
                if path.replace(b"/", b"\\").lower() != RESOURCE:
                    continue
                offset, packed, raw = struct.unpack_from("<III", record, PATH_BYTES)
                if packed <= 0 or offset < HEADER_SIZE + count * RECORD_SIZE or offset + packed > length:
                    raise BootstrapError(f"Invalid setup.lua offset in {pack}")
                digest = record[PATH_BYTES + 12:].decode("ascii")
                matches.append(Resource(pack, index, HEADER_SIZE + index * RECORD_SIZE,
                                        offset, packed, raw, digest))
    if len(matches) != 1:
        raise BootstrapError(
            f"Expected one setup.lua JMP resource, found {len(matches)} in {game} "
            f"({len(packs)} JMP files scanned). Check the selected game directory "
            "and client version."
        )
    return matches[0]


def read_resource(resource: Resource) -> bytes:
    with resource.pack.open("rb") as stream:
        stream.seek(resource.data_offset)
        packed = stream.read(resource.compressed_size)
    try:
        source = zlib.decompress(packed)
    except zlib.error as exc:
        raise BootstrapError("setup.lua decompression failed") from exc
    if len(source) != resource.raw_size or hashlib.md5(source).hexdigest() != resource.digest.lower():
        raise BootstrapError("setup.lua size or MD5 does not match JMP index")
    return source


def patch_source(source: bytes) -> bytes:
    if MARKER in source:
        return source
    if b"--E" in source:
        raise BootstrapError("Another external Lua bootstrap is installed")
    if source.count(LOAD_LINE) != 1:
        raise BootstrapError("setup.lua initialization anchor changed")
    # Remove complete-line comments only; keep block-comment bodies intact.
    if b"--[[" in source:
        compact = source
    else:
        compact = re.sub(rb"(?m)^[ \t]*--[^\r\n]*\r\n", b"", source)
        compact = re.sub(rb"(?:\r\n){3,}", b"\r\n\r\n", compact)
    return compact.replace(LOAD_LINE, LOAD_LINE + HOOK, 1)


def plan(game: Path) -> tuple[Resource, bytes, bytes]:
    resource = locate(game)
    before = read_resource(resource)
    after = patch_source(before)
    if after != before and len(zlib.compress(after, 9)) > resource.compressed_size:
        raise BootstrapError("Bootstrap exceeds the setup.lua JMP resource capacity")
    return resource, before, after


def install(game: Path, backup_dir: Path) -> str:
    resource, before, after = plan(game)
    if before == after:
        return "already installed"
    backup_dir.mkdir(parents=True, exist_ok=True)
    with resource.pack.open("rb") as stream:
        stream.seek(resource.record_offset)
        record = stream.read(RECORD_SIZE)
        stream.seek(resource.data_offset)
        packed_original = stream.read(resource.compressed_size)
    backup = backup_dir / "setup_jmp.json"
    backup.write_text(json.dumps({
        "pack": str(resource.pack), "index": resource.index,
        "record": record.hex(), "compressed": packed_original.hex(),
        "source_md5": hashlib.md5(before).hexdigest(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")
    packed = zlib.compress(after, 9)
    metadata = struct.pack("<III", resource.data_offset, len(packed), len(after))
    metadata += hashlib.md5(after).hexdigest().encode("ascii")
    try:
        with resource.pack.open("r+b") as stream:
            stream.seek(resource.data_offset)
            stream.write(packed.ljust(resource.compressed_size, b"\0"))
            stream.seek(resource.record_offset + PATH_BYTES)
            stream.write(metadata)
            stream.flush()
            os.fsync(stream.fileno())
        checked = locate(game)
        if read_resource(checked) != after or MARKER not in after:
            raise BootstrapError("Bootstrap verification failed")
    except Exception:
        restore(backup)
        raise
    return f"installed {resource.pack.name} #{resource.index}; backup {backup}"


def restore(backup: Path) -> None:
    data = json.loads(backup.read_text(encoding="utf-8"))
    pack = Path(data["pack"])
    record = bytes.fromhex(data["record"])
    compressed = bytes.fromhex(data["compressed"])
    if len(record) != RECORD_SIZE:
        raise BootstrapError("Invalid backup record length")
    offset, packed_size, _ = struct.unpack_from("<III", record, PATH_BYTES)
    if len(compressed) != packed_size:
        raise BootstrapError("Invalid backup payload length")
    with pack.open("r+b") as stream:
        stream.seek(offset)
        stream.write(compressed)
        stream.seek(HEADER_SIZE + int(data["index"]) * RECORD_SIZE)
        stream.write(record)
        stream.flush()
        os.fsync(stream.fileno())
    if hashlib.md5(read_resource(locate(pack.parent))).hexdigest() != data["source_md5"]:
        raise BootstrapError("Restored setup.lua failed verification")
