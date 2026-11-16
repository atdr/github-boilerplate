"""configure.sh rejects bad arguments before it makes any gh call."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "configure.sh"


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["example/repo", "--apply", "--diff"],
        ["example/repo", "--diff", "--apply"],
        ["example/repo", "--apply", "extra"],
        ["example/repo", "--bogus"],
        ["example/repo", ""],
    ],
)
def test_bad_arguments_print_usage_and_exit_2(args: list[str]) -> None:
    # An empty PATH means gh and every other command are unreachable, so exit 2
    # shows validation ended the script before any call that could change a repo.
    result = subprocess.run(
        ["/bin/bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env={"PATH": ""},
    )
    assert result.returncode == 2
    assert result.stderr.startswith("usage: ")
