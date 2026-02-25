#!/usr/bin/env python3
"""Export repository changes as a unified diff file.

By default the script writes a diff between the repository's initial commit and
HEAD to ``mother_ai_full.patch`` in the project root.  This provides a
self-contained view of the entire codebase that can be shared or reviewed in
other tools.  A specific starting revision or output file can be supplied via
CLI flags.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATCH = ROOT / "mother_ai_full.patch"


class DiffError(RuntimeError):
    """Raised when git diff cannot be produced."""


def run_git(*args: str) -> str:
    """Execute ``git`` with *args* and return stdout as text."""

    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise DiffError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def detect_root_commit() -> str:
    """Return the hash of the repository's initial commit."""

    return run_git("rev-list", "--max-parents=0", "HEAD").splitlines()[0]


def build_diff(since: str, until: str, staged: bool) -> str:
    """Return the diff text between *since* and *until* commits.

    When *staged* is True the diff is generated from the index to the working
    tree, which enables exporting uncommitted changes.
    """

    if staged:
        cmd = ["diff", "--cached", since]
    else:
        cmd = ["diff", since, until]
    result = subprocess.run(
        ["git", *cmd],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise DiffError(result.stderr.strip() or "git diff failed")
    return result.stdout


def write_patch(content: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        help="Starting revision for the diff (defaults to repository root commit).",
    )
    parser.add_argument(
        "--until",
        default="HEAD",
        help="Ending revision for the diff (defaults to HEAD).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PATCH,
        help="Destination file for the diff output.",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Export diff of staged changes instead of commit history.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    since = args.since or detect_root_commit()
    if args.staged:
        diff_text = build_diff(since, args.until, staged=True)
    else:
        diff_text = build_diff(since, args.until, staged=False)
    patch_path = write_patch(diff_text, args.output)
    print(f"Wrote diff to {patch_path}")


if __name__ == "__main__":
    try:
        main()
    except DiffError as exc:  # pragma: no cover - surfaced to CLI
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
