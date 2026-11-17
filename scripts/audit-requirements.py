#!/usr/bin/env python3
"""Turns uv's exported requirements into pip-audit's input.

Usage: audit-requirements.py OUT_PREFIX EXPORT [EXPORT ...]

Reads one or more `uv export --format requirements-txt` files, hashed, and
writes what pip-audit should check to OUT_PREFIX-1.txt, OUT_PREFIX-2.txt and
so on, each to be audited on its own. Runs in
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
- Environment markers are removed. pip-audit evaluates a marker against its
  own interpreter and skips the requirement when it is false, so a pin that
  only another supported Python installs would never be audited.
- A requirements file can list a package once, but a lock can hold several
  versions of it for different markers. File k holds the k-th version of each
  such package, with every other package in file 1.

Writes nothing when no requirement is left, since pip-audit refuses an empty
requirements file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
DIRECT_URL = re.compile(rf"\s*({NAME})\s*(?:\[[^\]]*\])?\s*@")
PIN = re.compile(rf"({NAME})\s*(?:\[[^\]]*\])?\s*===?\s*(\S+)")


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


def unmarked(block: list[str]) -> str:
    """The block as one string, its requirement's environment marker removed."""
    head = block[0].rstrip()
    continued = head.endswith("\\")
    if continued:
        head = head[:-1].rstrip()
    requirement, sep, options = head.partition(" --")
    if not requirement.lstrip().startswith("-"):
        requirement = requirement.split(";", 1)[0].rstrip()
    head = requirement + sep + options + (" \\" if continued else "")
    return "\n".join([head] + [line.rstrip() for line in block[1:]])


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def prepare(texts: list[str], label: str) -> list[str]:
    """The contents of each file pip-audit should check, in order.

    Prints a ::notice for each direct URL requirement it drops. A requirement
    that several exports share, or that the lock pins at one version under
    several markers, is kept once.
    """
    files: list[list[str]] = []
    seen: set[object] = set()
    versions: dict[str, list[str]] = {}
    skipped: list[str] = []
    for text in texts:
        for block in blocks(text):
            url = DIRECT_URL.match(block[0])
            if url:
                if url.group(1) not in skipped:
                    skipped.append(url.group(1))
                continue
            joined = unmarked(block)
            requirement = joined.split("\n", 1)[0].removesuffix("\\").partition(" --")[0]
            pin = PIN.fullmatch(requirement.strip())
            key: object = (normalize(pin.group(1)), pin.group(2)) if pin else joined
            if key in seen:
                continue
            seen.add(key)
            index = 0
            if pin:
                found = versions.setdefault(normalize(pin.group(1)), [])
                index = len(found)
                found.append(pin.group(2))
            while len(files) <= index:
                files.append([])
            files[index].append(joined)
    for name in skipped:
        print(
            f"::notice title=Not audited::{name} is a direct URL requirement of the {label}"
            " dependencies, which pip-audit cannot look up. The packages it depends on are"
            " still audited."
        )
    return ["\n".join(entries) + "\n" for entries in files]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    prefix = Path(argv[0])
    texts = [Path(name).read_text() for name in argv[1:]]
    for k, contents in enumerate(prepare(texts, prefix.name), start=1):
        Path(f"{prefix}-{k}.txt").write_text(contents)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
