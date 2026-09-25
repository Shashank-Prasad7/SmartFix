"""Verify imported official bytes and, when available, parent originals."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "data" / "official"
PARENT = ROOT.parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    manifest = json.loads((OFFICIAL / "manifest.json").read_text(encoding="utf-8"))
    original_items = [item for item in manifest["files"] if item["origin"]["kind"] == "original-file"]
    entry_count = sum(item["origin"]["kind"] == "zip-entry" for item in manifest["files"])
    parent_files = [PARENT / item["origin"]["parent_filename"] for item in original_items]
    # A teammate's checkout may include some original loose documents but
    # omit the large outer archive. Compare every available original while
    # always verifying every imported copy and nested archive entry.
    available_parent = {path for path in parent_files if path.is_file()}
    imported_ok = 0
    parent_ok = 0
    entry_ok = 0
    failures: list[str] = []
    for item in manifest["files"]:
        path = OFFICIAL / item["path"]
        try:
            contents = path.read_bytes()
        except OSError:
            failures.append(f"missing imported file: {item['path']}")
            continue
        if len(contents) != item["bytes"] or sha256(contents) != item["sha256"].upper():
            failures.append(f"import mismatch: {item['path']}")
        else:
            imported_ok += 1
        origin = item["origin"]
        if origin["kind"] == "original-file" and PARENT / origin["parent_filename"] in available_parent:
            parent = PARENT / origin["parent_filename"]
            try:
                original = parent.read_bytes()
            except OSError:
                failures.append(f"missing protected parent original: {origin['parent_filename']}")
                continue
            if original != contents:
                failures.append(f"protected parent mismatch: {origin['parent_filename']}")
            else:
                parent_ok += 1
        elif origin["kind"] == "zip-entry":
            container = OFFICIAL / origin["container"]
            try:
                with zipfile.ZipFile(container) as archive:
                    extracted = archive.read(origin["entry"])
            except (OSError, KeyError, zipfile.BadZipFile):
                failures.append(f"nested archive entry unavailable: {item['path']}")
                continue
            if extracted != contents:
                failures.append(f"nested archive entry mismatch: {item['path']}")
            else:
                entry_ok += 1
    print(f"IMPORTED: {imported_ok}/{len(manifest['files'])} hashes and sizes match")
    if available_parent:
        print(f"PROTECTED PARENT: {parent_ok}/{len(available_parent)} available originals match ({len(original_items)-len(available_parent)} absent in this checkout)")
    else:
        print("PROTECTED PARENT: skipped (original files absent in this checkout)")
    print(f"NESTED ENTRIES: {entry_ok}/{entry_count} byte-identical archive entries")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 0 if not failures and imported_ok == len(manifest["files"]) and parent_ok == len(available_parent) and entry_ok == entry_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
