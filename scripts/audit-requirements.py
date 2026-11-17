#!/usr/bin/env python3
"""Turns uv's exported requirements into pip-audit's input.

Usage: audit-requirements.py OUT_PREFIX EXPORT [EXPORT ...]

Reads one or more `uv export --format requirements-txt` files, hashed, and
writes what pip-audit should check to OUT_PREFIX-1.txt. Runs in
.github/workflows/python-ci.yml's audit job, which fetches it from this repo at
the caller's pinned commit. Standard library only: it runs on the runner's
interpreter, before anything is installed.

- Each requirement keeps its hashes, so `pip-audit --disable-pip` checks the
  pinned versions as they are without resolving anything.
- A direct URL requirement (`name @ url`, a Git dependency for one) is dropped
  with a ::notice. It has no version for pip-audit to look up, and uv exports
  it without hashes, which makes pip-audit reject the whole file. The export
  lists the whole resolved tree, so the packages it depends on are lines of
  their own and are still audited.

Writes nothing when no requirement is left, since pip-audit refuses an empty
requirements file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
DIRECT_URL = re.compile(rf"\s*({NAME})\s*(?:\[[^\]]*\])?\s*@")


def blocks(text: str) -> list[list[str]]:
    """Each requirement as its lines: the requirement, then any `\\` continuations."""
    found: list[list[str]] = []
    block: list[str] = []
    for line in text.splitlines():
        if not block and (not line.strip() or line.lstrip().startswith("#")):
            continue
        block.append(line)
        if not line.rstrip().endswith("\\"):
            found.append(block)
            block = []
    if block:
        found.append(block)
    return found


def prepare(texts: list[str], label: str) -> list[str]:
    """The blocks pip-audit should check, each as one string, in export order.

    Prints a ::notice for each direct URL requirement it drops. A block that
    several exports share is kept once.
    """
    kept: list[str] = []
    seen: set[str] = set()
    skipped: list[str] = []
    for text in texts:
        for block in blocks(text):
            url = DIRECT_URL.match(block[0])
            if url:
                if url.group(1) not in skipped:
                    skipped.append(url.group(1))
                continue
            joined = "\n".join(line.rstrip() for line in block)
            if joined not in seen:
                seen.add(joined)
                kept.append(joined)
    for name in skipped:
        print(
            f"::notice title=Not audited::{name} is a direct URL requirement of the {label}"
            " dependencies, which pip-audit cannot look up. The packages it depends on are"
            " still audited."
        )
    return kept


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    prefix = Path(argv[0])
    texts = [Path(name).read_text() for name in argv[1:]]
    kept = prepare(texts, prefix.name)
    if kept:
        Path(f"{prefix}-1.txt").write_text("\n".join(kept) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
