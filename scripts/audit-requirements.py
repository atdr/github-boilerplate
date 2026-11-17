#!/usr/bin/env python3
"""Turns uv's exported requirements into pip-audit's input.

Usage: audit-requirements.py OUT_PREFIX EXPORT [EXPORT ...]
       audit-requirements.py --selections PYPROJECT
       audit-requirements.py --index-options INSTALL

Reads one or more `uv export --format requirements-txt` files, hashed, and
writes what pip-audit should check to OUT_PREFIX-1.txt, OUT_PREFIX-2.txt and
so on, each to be audited on its own. Runs in
.github/workflows/python-ci.yml's audit job, which fetches it from this repo at
the caller's pinned commit. Standard library only, apart from tomli on Python
3.10: it runs on the runner's interpreter, beside nothing but pip-audit.

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

With --selections, prints instead one line per extra and dependency group that
PYPROJECT declares, `--extra NAME` or `--group NAME`, for the job to export
each on its own and pass every export here together. uv refuses one export of
`--all-extras --all-groups` when the project declares any of them conflicting.

With --index-options, prints the index options in INSTALL, the job's `install`
input, each followed by a NUL byte: index URLs, find links, trusted hosts and
--no-index. Without a uv.lock, the job installs the runtime tree with these
alone, so it resolves from the caller's indexes without the extras or anything
else `install` does. INSTALL is split as the shell would split its words,
quotes included, but nothing in it runs.
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    # Python 3.10, which `python-version` may name, has no tomllib. pip-audit,
    # installed into this same interpreter first, requires tomli, and `python
    # -I` still sees that interpreter's site-packages.
    import tomli as tomllib

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


def selections(pyproject: Path) -> list[str]:
    """`--extra NAME` for each extra, then `--group NAME` for each group."""
    if not pyproject.is_file():
        return []
    data = tomllib.loads(pyproject.read_text())
    extras = list(data.get("project", {}).get("optional-dependencies", {}))
    groups = list(data.get("dependency-groups", {}))
    # uv's older spelling of the dev group, which `--group dev` still selects.
    if data.get("tool", {}).get("uv", {}).get("dev-dependencies") and "dev" not in groups:
        groups.append("dev")
    return [f"--extra {name}" for name in extras] + [f"--group {name}" for name in groups]


# pip's options naming where packages come from, and the one flag among them.
INDEX_OPTIONS = {"--index-url", "-i", "--extra-index-url", "--find-links", "-f", "--trusted-host"}
INDEX_FLAGS = {"--no-index"}


def index_options(install: str) -> list[str]:
    """The index options in `install`, in order, each `--opt value` kept as two."""
    words = shlex.split(install)
    found: list[str] = []
    i = 0
    while i < len(words):
        word = words[i]
        if word in INDEX_OPTIONS:
            if i + 1 < len(words):
                found += [word, words[i + 1]]
                i += 1
        elif word.startswith("--") and word.partition("=")[0] in INDEX_OPTIONS and "=" in word:
            found.append(word)
        elif word in INDEX_FLAGS:
            found.append(word)
        i += 1
    return found


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--index-options":
        sys.stdout.write("".join(option + "\0" for option in index_options(argv[1])))
        return 0
    if len(argv) == 2 and argv[0] == "--selections":
        for line in selections(Path(argv[1])):
            print(line)
        return 0
    if len(argv) < 2 or argv[0].startswith("-"):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    prefix = Path(argv[0])
    texts = [Path(name).read_text() for name in argv[1:]]
    for k, contents in enumerate(prepare(texts, prefix.name), start=1):
        Path(f"{prefix}-{k}.txt").write_text(contents)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
