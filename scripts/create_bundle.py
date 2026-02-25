#!/usr/bin/env python3
"""Create a distributable zip archive of the Mother AI project.

The generated archive excludes Git metadata, existing zip bundles, and common
build artifacts so that the output contains only the source tree.  The script
is idempotent and safe to run repeatedly; by default it writes the bundle to
``mother_ai_system_latest.zip`` in the repository root, but a custom path can
be provided.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NAME = "mother_ai_system_latest.zip"


EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "logs",
    ".mypy_cache",
    ".pytest_cache",
}

EXCLUDE_SUFFIXES = {
    ".zip",
    ".pyc",
    ".pyo",
    ".pyd",
}


def should_skip(path: Path) -> bool:
    """Return True if *path* should be excluded from the archive."""
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def build_archive(destination: Path) -> Path:
    """Create the zip archive at *destination* and return the resulting path."""
    destination = destination.resolve()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in ROOT.rglob("*"):
            if file_path.is_dir():
                continue
            if should_skip(file_path.relative_to(ROOT)):
                continue
            zf.write(file_path, file_path.relative_to(ROOT))
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the generated archive. Defaults to the repository root.",
    )
    parser.add_argument(
        "--timestamp",
        action="store_true",
        help="Append a UTC timestamp to the generated filename for archival purposes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output:
        output_path = args.output
    else:
        name = DEFAULT_NAME
        if args.timestamp:
            stamp = dt.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            stem, suffix = os.path.splitext(DEFAULT_NAME)
            name = f"{stem}_{stamp}{suffix or '.zip'}"
        output_path = ROOT / name
    archive_path = build_archive(output_path)
    print(f"Created archive: {archive_path}")


if __name__ == "__main__":
    main()
