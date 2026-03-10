#!/usr/bin/env python3
"""dupes — fast duplicate file finder using content hashing.

Zero dependencies. Groups files by size first (cheap), then hashes
only size-matched files (expensive). Reports duplicates with wasted space.

Usage:
    dupes.py <path> [--min-size 1024] [--delete] [--json] [--ext .py,.js]
    dupes.py <path> --summary
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.tox',
             'dist', 'build', '.eggs', '.mypy_cache', '.pytest_cache'}


def find_files(root: str, min_size: int = 0, extensions: set = None) -> list[Path]:
    """Find all files under root, skipping common junk dirs."""
    files = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith('.')]
        for f in fns:
            if f.startswith('.'):
                continue
            p = Path(dp) / f
            if extensions and p.suffix.lower() not in extensions:
                continue
            try:
                if p.stat().st_size >= min_size:
                    files.append(p)
            except (OSError, PermissionError):
                pass
    return files


def hash_file(path: Path, chunk_size: int = 8192) -> str:
    """SHA-256 hash of file contents."""
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
    except (OSError, PermissionError):
        return ""
    return h.hexdigest()


def format_size(size: int) -> str:
    """Human-readable file size."""
    for unit in ('B', 'KB', 'MB', 'GB'):
        if abs(size) < 1024:
            return f"{size:.1f}{unit}" if unit != 'B' else f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def find_duplicates(root: str, min_size: int = 0, extensions: set = None) -> list[dict]:
    """Find duplicate files. Returns list of duplicate groups."""
    files = find_files(root, min_size, extensions)

    # Phase 1: group by size (fast filter)
    by_size = defaultdict(list)
    for f in files:
        try:
            by_size[f.stat().st_size].append(f)
        except OSError:
            pass

    # Only hash files with size matches
    candidates = []
    for size, paths in by_size.items():
        if len(paths) > 1:
            candidates.extend(paths)

    if not candidates:
        return []

    # Phase 2: group by hash (accurate)
    by_hash = defaultdict(list)
    for f in candidates:
        h = hash_file(f)
        if h:
            by_hash[h].append(f)

    # Build duplicate groups
    groups = []
    for h, paths in by_hash.items():
        if len(paths) > 1:
            size = paths[0].stat().st_size
            groups.append({
                "hash": h[:12],
                "size": size,
                "count": len(paths),
                "wasted": size * (len(paths) - 1),
                "files": [str(p) for p in sorted(paths)],
            })

    groups.sort(key=lambda g: g["wasted"], reverse=True)
    return groups


def cmd_scan(args):
    extensions = None
    if args.ext:
        extensions = {e.strip() if e.startswith('.') else f'.{e.strip()}' for e in args.ext.split(',')}

    root = args.path
    print(f"🔍 Scanning: {root}")

    groups = find_duplicates(root, args.min_size, extensions)

    if not groups:
        print("✅ No duplicate files found.")
        return

    if args.json:
        print(json.dumps(groups, indent=2))
        return

    total_wasted = sum(g["wasted"] for g in groups)
    total_dupes = sum(g["count"] - 1 for g in groups)

    if args.summary:
        print(f"📊 Summary:")
        print(f"   Duplicate groups: {len(groups)}")
        print(f"   Duplicate files:  {total_dupes}")
        print(f"   Wasted space:     {format_size(total_wasted)}")
        print()
        # Top 5 by wasted space
        print("   🏆 Biggest offenders:")
        for g in groups[:5]:
            fname = Path(g["files"][0]).name
            print(f"     {fname} × {g['count']} ({format_size(g['wasted'])} wasted)")
        return

    print(f"📊 Found {len(groups)} duplicate groups ({total_dupes} extra files, {format_size(total_wasted)} wasted)")
    print()

    for i, g in enumerate(groups, 1):
        print(f"  Group {i}: {format_size(g['size'])} × {g['count']} files ({format_size(g['wasted'])} wasted) [{g['hash']}]")
        for f in g["files"]:
            print(f"    {f}")
        print()

    if args.delete:
        print("🗑️  Delete mode: keeping first file in each group, removing rest.")
        confirm = input("   Proceed? [y/N] ").strip().lower()
        if confirm == 'y':
            deleted = 0
            freed = 0
            for g in groups:
                for f in g["files"][1:]:  # keep first
                    try:
                        size = Path(f).stat().st_size
                        Path(f).unlink()
                        deleted += 1
                        freed += size
                        print(f"   ✗ {f}")
                    except OSError as e:
                        print(f"   ⚠ {f}: {e}")
            print(f"\n   Deleted {deleted} files, freed {format_size(freed)}")
        else:
            print("   Cancelled.")


def main():
    parser = argparse.ArgumentParser(description="dupes — duplicate file finder")
    parser.add_argument("path", help="Directory to scan")
    parser.add_argument("--min-size", type=int, default=0, help="Minimum file size in bytes")
    parser.add_argument("--ext", help="Filter by extensions (comma-separated)")
    parser.add_argument("--delete", action="store_true", help="Interactively delete duplicates")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--summary", action="store_true", help="Summary only")
    args = parser.parse_args()
    cmd_scan(args)


if __name__ == "__main__":
    main()
