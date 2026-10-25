#!/usr/bin/env python3
"""Checks a repository against the conventions in STANDARDS.md.

Usage: check-conventions.py [REPO_ROOT]

Each rule here exists because the prose version of it drifted at least once in
a real repo. Enforcing it is what keeps it true. Every finding names its rule,
and STANDARDS.md has a section per rule saying why.

Runs in CI through .github/workflows/conventions.yml, and locally by hand.
Exits 1 if anything fails.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import yaml

# The single list of commit types. conventional.yml's `types` default must
# match it, and so must every commitlint or pre-commit config.
COMMIT_TYPES = ["feat", "fix", "perf", "refactor", "test", "docs", "chore", "ci"]

PR_ONLY_EVENTS = {"pull_request", "pull_request_target"}
COMMITLINT_CONFIGS = [
    "commitlint.config.js",
    "commitlint.config.cjs",
    "commitlint.config.mjs",
    "commitlint.config.ts",
]


class Findings:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[tuple[str, str, str]] = []

    def add(self, path: Path, rule: str, message: str) -> None:
        self.errors.append((str(path.relative_to(self.root)), rule, message))


def load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)


def triggers(workflow: dict) -> set[str]:
    # PyYAML follows YAML 1.1, where a bare `on` key parses as boolean True.
    on = workflow.get("on", workflow.get(True))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on)
    return set()


def check_workflows(root: Path, f: Findings) -> None:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        return
    for path in sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")]):
        workflow = load_yaml(path) or {}

        # GitHub labels a check `<workflow name> / <job name>` and never shows
        # the filename, so the name is what maps a check back to its file.
        if workflow.get("name") != path.stem:
            f.add(
                path,
                "workflow-name",
                f"top-level name must be {path.stem!r} (the filename stem), "
                f"found {workflow.get('name')!r}; describe the job instead",
            )

        if "permissions" not in workflow:
            f.add(
                path,
                "workflow-permissions",
                "set top-level permissions (contents: read, or {}) and widen "
                "them per job",
            )

        for job_id, job in (workflow.get("jobs") or {}).items():
            # A job that calls a reusable workflow takes no timeout of its own;
            # the called workflow's jobs carry it.
            if "uses" in job:
                continue
            if "timeout-minutes" not in job:
                f.add(
                    path,
                    "job-timeout",
                    f"job {job_id!r} needs timeout-minutes; GitHub's default "
                    "is six hours, and a stalled fetch never fails on its own",
                )

        # Superseded runs may be cancelled on pull requests only. On main every
        # commit keeps its own result, and a release, publish or deploy
        # cancelled halfway can leave a tag with no package.
        if not triggers(workflow) <= PR_ONLY_EVENTS:
            blocks = [("workflow", workflow.get("concurrency"))] + [
                (f"job {job_id!r}", job.get("concurrency"))
                for job_id, job in (workflow.get("jobs") or {}).items()
            ]
            for where, concurrency in blocks:
                if isinstance(concurrency, dict) and concurrency.get("cancel-in-progress") is True:
                    f.add(
                        path,
                        "concurrency",
                        f"{where}: cancel-in-progress: true on a workflow with "
                        "non-PR triggers; use ${{ github.event_name == "
                        "'pull_request' }} for CI, or false to queue releases "
                        "and deploys",
                    )

        # A types override would split the one commit type list in two.
        for job_id, job in (workflow.get("jobs") or {}).items():
            uses = str(job.get("uses", ""))
            if uses.endswith("/conventional.yml") or "/conventional.yml@" in uses:
                if "types" in (job.get("with") or {}):
                    f.add(
                        path,
                        "commit-types",
                        f"job {job_id!r} overrides conventional.yml's types; "
                        "change the list in github-boilerplate instead",
                    )


def check_dependabot(root: Path, f: Findings) -> None:
    path = root / ".github" / "dependabot.yml"
    if not path.is_file():
        f.add(root, "dependabot", "missing .github/dependabot.yml")
        return
    config = load_yaml(path) or {}
    updates = config.get("updates") or []

    ecosystems = [u.get("package-ecosystem") for u in updates]
    if "github-actions" not in ecosystems:
        f.add(
            path,
            "dependabot",
            "add a github-actions entry: major-tag pins never cross a major "
            "version on their own",
        )

    for update in updates:
        ecosystem = update.get("package-ecosystem")
        message = update.get("commit-message") or {}
        if "prefix" not in message:
            f.add(
                path,
                "dependabot-prefix",
                f"{ecosystem}: set commit-message.prefix so release-please "
                "treats the bump deliberately",
            )
        if ecosystem in {"npm", "pip", "uv"}:
            dev = str(message.get("prefix-development", ""))
            if not dev.startswith("chore"):
                f.add(
                    path,
                    "dependabot-prefix",
                    f"{ecosystem}: prefix-development must be chore: dev "
                    "dependencies reach nobody and should not cut a release",
                )
        # A security-updates group once filtered a high advisory out of its own
        # job and still reported success. Advisories stay ungrouped.
        for name, group in (update.get("groups") or {}).items():
            if (group or {}).get("applies-to") == "security-updates":
                f.add(
                    path,
                    "dependabot-security-group",
                    f"{ecosystem}: group {name!r} batches security updates; "
                    "leave advisories ungrouped",
                )


def check_instructions(root: Path, f: Findings) -> None:
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    if not agents.is_file():
        f.add(root, "agents-md", "missing AGENTS.md")
    if not claude.is_symlink() or os.readlink(claude) != "AGENTS.md":
        f.add(
            root,
            "agents-md",
            "CLAUDE.md must be a symlink to AGENTS.md, so every tool reads "
            "one file",
        )


def check_gitattributes(root: Path, f: Findings) -> None:
    path = root / ".gitattributes"
    lines = path.read_text().splitlines() if path.is_file() else []
    if not any(line.split() == ["*", "text=auto"] for line in lines):
        f.add(root, "gitattributes", ".gitattributes must contain '* text=auto'")


def type_list(text: str) -> list[str] | None:
    match = re.search(r"['\"]type-enum['\"]\s*:\s*\[[^\[]*\[([^\]]*)\]", text)
    if not match:
        return None
    return re.findall(r"['\"]([a-z]+)['\"]", match.group(1))


def check_commit_types(root: Path, f: Findings) -> None:
    for name in COMMITLINT_CONFIGS:
        path = root / name
        if not path.is_file():
            continue
        types = type_list(path.read_text())
        if types is None:
            f.add(
                path,
                "commit-types",
                "set a type-enum rule; config-conventional's own list allows "
                "build, style and revert, which the standard does not",
            )
        elif sorted(types) != sorted(COMMIT_TYPES):
            f.add(
                path,
                "commit-types",
                f"type-enum must be {COMMIT_TYPES}, found {types}",
            )

    path = root / ".pre-commit-config.yaml"
    if path.is_file():
        config = load_yaml(path) or {}
        for repo in config.get("repos") or []:
            for hook in repo.get("hooks") or []:
                if hook.get("id") != "conventional-pre-commit":
                    continue
                args = [a for a in hook.get("args") or [] if not a.startswith("-")]
                if sorted(args) != sorted(COMMIT_TYPES):
                    f.add(
                        path,
                        "commit-types",
                        f"conventional-pre-commit args must be {COMMIT_TYPES}, "
                        f"found {args}",
                    )


def check_release_please(root: Path, f: Findings) -> None:
    config = root / "release-please-config.json"
    manifest = root / ".release-please-manifest.json"
    if config.is_file() != manifest.is_file():
        f.add(
            root,
            "release-please",
            "release-please-config.json and .release-please-manifest.json "
            "come as a pair",
        )


def check_codecov(root: Path, f: Findings) -> None:
    path = root / "codecov.yml"
    if not path.is_file():
        return
    status = ((load_yaml(path) or {}).get("coverage") or {}).get("status") or {}
    for kind in ("project", "patch"):
        default = (status.get(kind) or {}).get("default") or {}
        if default.get("informational") is not True:
            f.add(
                path,
                "codecov",
                f"coverage.status.{kind}.default.informational must be true: "
                "coverage reports, it does not gate",
            )


PRETTIER_CONFIGS = [
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    ".prettierrc.js",
    ".prettierrc.cjs",
    ".prettierrc.mjs",
    "prettier.config.js",
    "prettier.config.cjs",
    "prettier.config.mjs",
]


def check_markdown_formatter(root: Path, f: Findings) -> None:
    # mdformat and Prettier format Markdown differently, so a repo running
    # both would have each undo the other. mdformat owns it.
    if not (root / ".mdformat.toml").is_file():
        return
    package = root / "package.json"
    uses_prettier = any((root / name).is_file() for name in PRETTIER_CONFIGS) or (
        package.is_file() and '"prettier":' in package.read_text()
    )
    if not uses_prettier:
        return
    ignore = root / ".prettierignore"
    lines = ignore.read_text().splitlines() if ignore.is_file() else []
    if not {"*.md", "**/*.md"} & {line.strip() for line in lines}:
        f.add(
            root,
            "markdown-formatter",
            "add *.md to .prettierignore: mdformat formats Markdown, and "
            "Prettier would undo it",
        )


CHECKS = [
    check_workflows,
    check_dependabot,
    check_instructions,
    check_gitattributes,
    check_commit_types,
    check_release_please,
    check_codecov,
    check_markdown_formatter,
]


def run(root: Path) -> list[tuple[str, str, str]]:
    findings = Findings(root.resolve())
    for check in CHECKS:
        check(findings.root, findings)
    return findings.errors


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".")
    errors = run(root)
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"
    for path, rule, message in errors:
        if annotate:
            print(f"::error file={path},title={rule}::{message}")
        else:
            print(f"{path}: [{rule}] {message}")
    if errors:
        print(f"\n{len(errors)} convention(s) not met. See STANDARDS.md.")
        return 1
    print("All conventions met.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
