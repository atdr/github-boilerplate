"""The mdformat pins in the template's pre-commit configs must equal the ones
CI installs from scripts/requirements-markdown.txt. Dependabot bumps that file
and nothing else, so without this a local hook and CI format differently."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = ROOT / "scripts" / "requirements-markdown.txt"
MDFORMAT_REPO = "https://github.com/hukkin/mdformat"
PACKAGE = re.compile(r"^(mdformat[\w.-]*)==(\S+)$")


def normalize(name: str) -> str:
    """Compare package names as pip does."""
    return re.sub(r"[-_.]+", "-", name).lower()


def ci_pins() -> dict[str, str]:
    pins = {}
    for line in REQUIREMENTS.read_text().splitlines():
        match = PACKAGE.match(line.strip())
        if match:
            pins[normalize(match.group(1))] = match.group(2)
    return pins


def hook_pins(config: Path) -> dict[str, str]:
    """The mdformat pins one pre-commit config carries: the hook's `rev` is the
    mdformat version (hukkin/mdformat tags carry no `v`, but strip one if a tag
    ever does), and each additional dependency is a plugin pin."""
    pins = {}
    for repo in yaml.safe_load(config.read_text())["repos"]:
        if repo["repo"].removesuffix(".git") != MDFORMAT_REPO:
            continue
        pins["mdformat"] = str(repo["rev"]).removeprefix("v")
        for hook in repo["hooks"]:
            for dep in hook.get("additional_dependencies", []):
                match = PACKAGE.match(dep)
                assert match, f"{config}: unpinned mdformat dependency {dep!r}"
                pins[normalize(match.group(1))] = match.group(2)
    return pins


def test_template_pre_commit_configs_are_found():
    # A guard that globs nothing passes forever.
    assert list((ROOT / "template").rglob(".pre-commit-config.yaml"))


def test_template_mdformat_pins_match_the_ci_pins():
    expected = ci_pins()
    assert "mdformat" in expected
    for config in sorted((ROOT / "template").rglob(".pre-commit-config.yaml")):
        found = hook_pins(config)
        if not found:
            continue
        rel = config.relative_to(ROOT)
        assert found == expected, (
            f"{rel} pins {found}, but {REQUIREMENTS.relative_to(ROOT)} pins "
            f"{expected}. Change both together."
        )
