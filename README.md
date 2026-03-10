# dupes

Fast duplicate file finder using content hashing. Zero dependencies.

## Usage

```bash
# Find all duplicates
python3 dupes.py /path/to/dir

# Only files >= 1MB
python3 dupes.py . --min-size 1048576

# Only Python files
python3 dupes.py . --ext .py,.pyi

# Quick summary
python3 dupes.py . --summary

# JSON output
python3 dupes.py . --json

# Interactive delete (keeps first, removes rest)
python3 dupes.py . --delete
```

## How It Works

1. **Phase 1:** Groups files by size (fast, eliminates most non-dupes)
2. **Phase 2:** SHA-256 hashes only size-matched files (accurate)
3. Reports groups sorted by wasted space

## Philosophy

One file. Zero deps. Does one thing well.
