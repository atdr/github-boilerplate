"""The boilerplate's own guards: each overlay applies cleanly and passes its
own conventions, the checker catches what it claims to, and the places that
must agree with each other do."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
OVERLAYS = ["core", "node", "python", "tex"]
PIN = re.compile(r"uses: atdr/github-boilerplate/\S+@\S+")

spec = importlib.util.spec_from_file_location(
    "check_conventions", ROOT / "scripts" / "check-conventions.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def apply(overlay: str, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(ROOT / "scripts" / "apply.sh"), overlay, str(target)],
        check=True,
        capture_output=True,
    )
    return target



def diff(overlay: str, target: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(ROOT / "scripts" / "apply.sh"), overlay, str(target), "--diff"],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("overlay", OVERLAYS)
def test_diff_finds_a_fresh_copy_unchanged(overlay, tmp_path):
    result = diff(overlay, apply(overlay, tmp_path / "repo"))
    assert result.returncode == 0, result.stdout
    assert "every copied file matches" in result.stdout


def test_diff_shows_an_edited_copy_and_a_missing_one(tmp_path):
    repo = apply("node", tmp_path / "repo")
    ci = repo / ".github/workflows/ci.yml"
    ci.write_text(ci.read_text().replace("scripts: lint format:check test", "scripts: lint test"))
    (repo / "SECURITY.md").unlink()
    result = diff("node", repo)
    assert result.returncode == 1
    assert "-      scripts: lint format:check test" in result.stdout
    assert "+      scripts: lint test" in result.stdout
    assert "missing from the repo:\n    SECURITY.md" in result.stdout


def test_apply_rejects_more_than_one_option(tmp_path):
    repo = apply("core", tmp_path / "repo")
    (repo / "SECURITY.md").write_text("edited\n")
    result = subprocess.run(
        [str(ROOT / "scripts" / "apply.sh"), "core", str(repo), "--force", "--diff"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert (repo / "SECURITY.md").read_text() == "edited\n"


def test_diff_leaves_the_skeletons_alone(tmp_path):
    repo = apply("core", tmp_path / "repo")
    (repo / "README.md").write_text("# Something else entirely\n")
    result = diff("core", repo)
    assert result.returncode == 0, result.stdout
    assert "README.md" in result.stdout.splitlines()[-1]

def rules(root: Path) -> set[str]:
    return {rule for _, rule, _ in checker.run(root)}


@pytest.mark.parametrize("overlay", OVERLAYS)
def test_overlay_meets_its_own_conventions(overlay, tmp_path):
    assert checker.run(apply(overlay, tmp_path / overlay)) == []


@pytest.mark.parametrize("overlay", OVERLAYS)
def test_applied_markdown_is_formatted(overlay, tmp_path):
    # Checked here rather than in template/ itself, where the placeholders
    # (__REPO__) read as bold.
    root = apply(overlay, tmp_path / overlay)
    result = subprocess.run(
        [sys.executable, "-m", "mdformat", "--check", "."],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_this_repo_meets_its_own_conventions():
    assert checker.run(ROOT) == []


def test_apply_leaves_existing_files_alone(tmp_path):
    (tmp_path / "README.md").write_text("mine\n")
    apply("core", tmp_path)
    assert (tmp_path / "README.md").read_text() == "mine\n"


def test_overlay_file_replaces_core_file(tmp_path):
    apply("node", tmp_path)
    applied = (tmp_path / ".github" / "dependabot.yml").read_text()
    assert applied == (ROOT / "template/node/.github/dependabot.yml").read_text()


def test_apply_fills_every_placeholder(tmp_path):
    apply("node", tmp_path)
    for path in tmp_path.rglob("*"):
        if path.is_file() and not path.is_symlink():
            text = path.read_text()
            assert "__OWNER__" not in text and "__REPO__" not in text, path
            assert "x-release-please-version" not in text, path


# --- the checker catches what it claims to -------------------------------


@pytest.fixture
def repo(tmp_path):
    return apply("node", tmp_path / "repo")


def edit_yaml(path: Path, change) -> None:
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_catches_a_workflow_named_for_what_it_does(repo):
    edit_yaml(repo / ".github/workflows/ci.yml", lambda w: w.update(name="CI"))
    assert "workflow-name" in rules(repo)


def test_catches_a_job_without_a_timeout(repo):
    def drop(w):
        del w["jobs"]["gate"]["timeout-minutes"]

    edit_yaml(repo / ".github/workflows/ci.yml", drop)
    assert "job-timeout" in rules(repo)


def test_catches_cancelling_runs_on_main(repo):
    def cancel(w):
        w["concurrency"]["cancel-in-progress"] = True

    edit_yaml(repo / ".github/workflows/ci.yml", cancel)
    assert "concurrency" in rules(repo)


def test_catches_a_ci_group_shared_on_main(repo):
    def share(w):
        w["concurrency"]["group"] = "${{ github.workflow }}-${{ github.ref }}"

    edit_yaml(repo / ".github/workflows/ci.yml", share)
    assert "concurrency" in rules(repo)


def test_allows_cancelling_a_pr_only_workflow(repo):
    text = (repo / ".github/workflows/pull-request.yml").read_text()
    assert "cancel-in-progress: true" in text
    assert "concurrency" not in rules(repo)


def test_catches_a_security_updates_group(repo):
    def group(d):
        d["updates"][0]["groups"]["security"] = {"applies-to": "security-updates"}

    edit_yaml(repo / ".github/dependabot.yml", group)
    assert "dependabot-security-group" in rules(repo)


def test_catches_a_releasing_dev_dependency_prefix(repo):
    def prefix(d):
        d["updates"][0]["commit-message"]["prefix-development"] = "fix"

    edit_yaml(repo / ".github/dependabot.yml", prefix)
    assert "dependabot-prefix" in rules(repo)


def test_catches_claude_md_as_a_real_file(repo):
    (repo / "CLAUDE.md").unlink()
    (repo / "CLAUDE.md").write_text("split instructions\n")
    assert "agents-md" in rules(repo)


def test_catches_a_drifted_commit_type_list(repo):
    path = repo / "commitlint.config.js"
    path.write_text(path.read_text().replace("'perf', ", ""))
    assert "commit-types" in rules(repo)


def test_catches_a_drifted_pre_commit_type_list(tmp_path):
    root = apply("python", tmp_path)
    path = root / ".pre-commit-config.yaml"
    path.write_text(path.read_text().replace(" perf,", ""))
    assert "commit-types" in rules(root)


def test_catches_coverage_as_a_gate(repo):
    def gate(c):
        c["coverage"]["status"]["patch"]["default"]["informational"] = False

    edit_yaml(repo / "codecov.yml", gate)
    assert "codecov" in rules(repo)


# --- things that must agree --------------------------------------------------


def test_conventional_types_match_the_checker():
    workflow = yaml.safe_load((ROOT / ".github/workflows/conventional.yml").read_text())
    default = workflow[True]["workflow_call"]["inputs"]["types"]["default"]
    assert default.split() == checker.COMMIT_TYPES


def test_every_template_pin_is_rewritten_on_release():
    config = json.loads((ROOT / "release-please-config.json").read_text())
    entries = config["packages"]["."]["extra-files"]
    # A bare path to a .yml file gets release-please's YAML updater, which
    # looks for a `version` key and ignores the x-release-please-version
    # markers. Only the generic updater reads them.
    assert all(isinstance(e, dict) and e.get("type") == "generic" for e in entries)
    extra_files = {e["path"] for e in entries}
    pinned = set()
    for path in (ROOT / "template").rglob("*.yml"):
        for line in path.read_text().splitlines():
            if PIN.search(line):
                assert line.endswith("# x-release-please-version"), (path, line)
                pinned.add(str(path.relative_to(ROOT)))
    assert pinned == extra_files


def gate_names(path: Path) -> set[str]:
    workflow = yaml.safe_load(path.read_text())
    return {
        job["name"]
        for job in workflow["jobs"].values()
        if str(job.get("name", "")).endswith(" gate")
    }


def test_ruleset_requires_exactly_the_core_gates():
    ruleset = json.loads((ROOT / "settings/ruleset-main.json").read_text())
    (checks,) = [r for r in ruleset["rules"] if r["type"] == "required_status_checks"]
    required = {c["context"] for c in checks["parameters"]["required_status_checks"]}
    workflows = ROOT / "template/core/.github/workflows"
    assert required == set().union(*(gate_names(p) for p in workflows.glob("*.yml")))


@pytest.mark.parametrize("overlay", ["node", "python"])
def test_language_overlays_have_the_ci_gate_configure_requires(overlay):
    assert gate_names(ROOT / f"template/{overlay}/.github/workflows/ci.yml") == {"ci gate"}
    assert '"ci gate"' in (ROOT / "scripts/ruleset.jq").read_text()


def ruleset(*gates: str) -> dict:
    result = subprocess.run(
        ["jq", "--arg", "gates", "".join(f"{g}\n" for g in gates),
         "-f", str(ROOT / "scripts/ruleset.jq"), str(ROOT / "settings/ruleset-main.json")],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def required_checks(rules: dict) -> list[str] | None:
    found = [r for r in rules["rules"] if r["type"] == "required_status_checks"]
    if not found:
        return None
    return [c["context"] for c in found[0]["parameters"]["required_status_checks"]]


@pytest.mark.parametrize(
    "gates, expected",
    [
        (("pull-request gate", "checks gate", "ci gate"), ["pull-request gate", "checks gate", "ci gate"]),
        (("pull-request gate", "checks gate"), ["pull-request gate", "checks gate"]),
        (("checks gate",), ["checks gate"]),
        ((), None),
    ],
)
def test_ruleset_requires_only_the_gates_present(gates, expected):
    rules = ruleset(*gates)
    assert required_checks(rules) == expected
    # Everything else in the ruleset applies whatever the repo's workflows.
    assert {"deletion", "non_fast_forward", "pull_request"} <= {r["type"] for r in rules["rules"]}


def test_template_claude_md_is_a_symlink():
    assert os.readlink(ROOT / "template/core/CLAUDE.md") == "AGENTS.md"


def test_apply_pins_and_strips_markers_after_a_release(tmp_path):
    # After the first release, release-please has rewritten the template pins
    # from v0.0.0 to the released version. apply.sh must still strip the marker.
    copy = tmp_path / "boilerplate"
    shutil.copytree(ROOT, copy, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    (copy / ".release-please-manifest.json").write_text('{".": "0.3.1"}\n')
    for path in (copy / "template").rglob("*.yml"):
        path.write_text(path.read_text().replace("@v0.0.0 #", "@v0.3.1 #"))
    target = tmp_path / "repo"
    target.mkdir()
    subprocess.run(
        [str(copy / "scripts" / "apply.sh"), "node", str(target)],
        check=True,
        capture_output=True,
    )
    ci = (target / ".github/workflows/ci.yml").read_text()
    assert "node-ci.yml@v0.3.1\n" in ci
    assert "x-release-please-version" not in ci


def test_apply_ignores_a_non_github_remote(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "https://gitlab.com/me/proj.git"],
        check=True,
    )
    apply("core", tmp_path)
    assert "/atdr/" + tmp_path.name + "/" in (tmp_path / "SECURITY.md").read_text()


@pytest.mark.parametrize("overlay", ["core", "tex"])
def test_readme_has_no_ci_badges_without_a_ci_workflow(overlay, tmp_path):
    readme = (apply(overlay, tmp_path) / "README.md").read_text()
    assert "[![CI]" not in readme and "[![Coverage]" not in readme


@pytest.mark.parametrize("overlay", OVERLAYS)
def test_every_overlay_ignores_secrets(overlay, tmp_path):
    ignored = (apply(overlay, tmp_path) / ".gitignore").read_text().splitlines()
    assert {".env", ".env.*", "*.pem", "*.key"} <= set(ignored)


def test_catches_a_cancelling_job_on_main(repo):
    def cancel(w):
        w["jobs"]["gate"]["concurrency"] = {"group": "x", "cancel-in-progress": True}

    edit_yaml(repo / ".github/workflows/ci.yml", cancel)
    assert "concurrency" in rules(repo)


def test_dependabot_covers_every_template_workflow_directory():
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    (actions,) = [u for u in config["updates"] if u["package-ecosystem"] == "github-actions"]
    expected = {"/"} | {
        "/" + str(p.relative_to(ROOT)) for p in (ROOT / "template").glob("*/.github/workflows")
    }
    assert set(actions["directories"]) == expected


def test_dependabot_bumps_each_action_once_across_directories():
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
    (actions,) = [u for u in config["updates"] if u["package-ecosystem"] == "github-actions"]
    assert [g.get("group-by") for g in actions["groups"].values()] == ["dependency-name"]


@pytest.mark.parametrize("overlay", ["node", "python"])
def test_language_overlays_group_development_updates(overlay):
    config = yaml.safe_load((ROOT / f"template/{overlay}/.github/dependabot.yml").read_text())
    (packages,) = [u for u in config["updates"] if u["package-ecosystem"] != "github-actions"]
    groups = list((packages.get("groups") or {}).values())
    assert {"dependency-type": "development", "update-types": ["minor", "patch"]} in groups


def test_every_template_release_pr_workflow_says_to_approve_its_runs():
    for path in (ROOT / "template").glob("*/.github/workflows/*.yml"):
        text = path.read_text()
        if "googleapis/release-please-action" in text:
            assert "Approve and run" in text, path


def all_workflows():
    return sorted(
        [*(ROOT / ".github/workflows").glob("*.yml"), *(ROOT / "template").glob("*/.github/workflows/*.yml")]
    )


def test_every_gate_is_the_same_gate():
    # The gate is copied into each caller rather than shared, because a
    # required check is named by its own job. This keeps the copies identical.
    gates = []
    for path in all_workflows():
        for job in yaml.safe_load(path.read_text())["jobs"].values():
            if str(job.get("name", "")).endswith(" gate"):
                body = {k: v for k, v in job.items() if k not in ("name", "needs")}
                gates.append((path.relative_to(ROOT), body))
    assert len(gates) > 1
    first = gates[0][1]
    assert first["if"] == "${{ !cancelled() }}"
    for path, body in gates:
        assert body == first, path


def test_settings_allow_squash_merges_only():
    repository = json.loads((ROOT / "settings/repository.json").read_text())
    assert repository["allow_squash_merge"] is True
    assert repository["allow_merge_commit"] is False
    assert repository["allow_rebase_merge"] is False
    assert repository["squash_merge_commit_title"] == "PR_TITLE"


def test_only_release_please_repos_let_actions_open_prs():
    base = json.loads((ROOT / "settings/actions-workflow.json").read_text())
    assert base == {
        "default_workflow_permissions": "read",
        "can_approve_pull_request_reviews": False,
    }
    extra = json.loads((ROOT / "settings/actions-workflow-release-please.json").read_text())
    assert extra == {"can_approve_pull_request_reviews": True}


def test_configure_sends_every_settings_file():
    script = (ROOT / "scripts/configure.sh").read_text()
    for path in (ROOT / "settings").glob("*.json"):
        assert f"$settings/{path.name}" in script, path.name


def environments(workflow: str) -> list[str]:
    result = subprocess.run(
        ["awk", "-f", str(ROOT / "scripts/workflow-environments.awk")],
        input=workflow,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


@pytest.mark.parametrize(
    "declaration",
    [
        "environment: pypi",
        "environment: 'pypi'",
        'environment: "pypi"',
        "environment: pypi  # trusted publisher",
        "environment: { name: pypi, url: https://pypi.org }",
        "environment: {name: 'pypi'}",
        "environment:\n      name: pypi\n      url: https://pypi.org",
        "environment:\n      url: https://pypi.org\n      name: \"pypi\"",
    ],
)
def test_configure_reads_each_environment_form(declaration):
    workflow = f"jobs:\n  publish:\n    {declaration}\n    runs-on: ubuntu-latest\n"
    assert environments(workflow) == ["pypi"]


def test_configure_ignores_commented_and_unrelated_names():
    workflow = (
        "jobs:\n"
        "  a:\n"
        "    # environment: pypi\n"
        "    environment:\n"
        "      name: npm-prerelease\n"
        "    steps:\n"
        "      - name: Publish\n"
    )
    assert environments(workflow) == ["npm-prerelease"]


@pytest.mark.parametrize("overlay", ["node", "python"])
def test_configure_finds_the_template_environments(overlay):
    workflows = ROOT / f"template/{overlay}/.github/workflows"
    text = "".join(path.read_text() for path in sorted(workflows.glob("*.yml")))
    expected = {"node": {"npm-release", "npm-prerelease"}, "python": {"pypi"}}[overlay]
    assert set(environments(text)) == expected


BADGE = re.compile(r"^\[!\[[^\]]+\]\((?P<image>[^)]+)\)\]\([^)]+\)$")


@pytest.mark.parametrize("readme", ["README.md", "template/core/README.md"])
def test_badges_are_flat_square_shields(readme):
    badges = [m for line in (ROOT / readme).read_text().splitlines() if (m := BADGE.match(line))]
    assert badges
    for badge in badges:
        image = badge["image"]
        assert image.startswith("https://img.shields.io/"), image
        assert "style=flat-square" in image, image
        if "/actions/workflow/status/" in image:
            assert "branch=main" in image, image


def test_first_release_is_pre_1_0():
    # With no earlier tag, release-please ignores the manifest's 0.0.0 and
    # cuts its default initial version, 1.0.0, unless told otherwise.
    config = json.loads((ROOT / "release-please-config.json").read_text())
    package = config["packages"]["."]
    assert package["initial-version"] == "0.1.0"
    assert package["bump-minor-pre-major"] is True


def test_catches_prettier_and_mdformat_both_owning_markdown(repo):
    (repo / ".prettierignore").write_text("node_modules/\n")
    assert "markdown-formatter" in rules(repo)


def test_prettier_without_mdformat_is_left_alone(repo):
    (repo / ".prettierignore").write_text("node_modules/\n")
    (repo / ".mdformat.toml").unlink()
    assert "markdown-formatter" not in rules(repo)


@pytest.mark.parametrize("overlay", ["core", "node", "python"])
def test_boilerplate_pins_move_together(overlay):
    # One PR per boilerplate release, not one per pinned workflow file.
    config = yaml.safe_load((ROOT / f"template/{overlay}/.github/dependabot.yml").read_text())
    (actions,) = [u for u in config["updates"] if u["package-ecosystem"] == "github-actions"]
    assert actions["groups"]["github-boilerplate"]["patterns"] == ["atdr/github-boilerplate*"]


def test_catches_a_placeholder_copied_by_hand(repo):
    shutil.copy(ROOT / "template/core/.github/FUNDING.yml", repo / ".github/FUNDING.yml")
    assert "placeholders" in rules(repo)


def test_prerelease_runs_queue_per_version():
    workflow = yaml.safe_load((ROOT / "template/node/.github/workflows/publish-prerelease.yml").read_text())
    assert workflow["concurrency"]["group"] == "${{ github.workflow }}-${{ inputs.version }}"
    assert workflow["concurrency"]["cancel-in-progress"] is False


@pytest.mark.parametrize("config", [".prettierrc.json5", ".prettierrc.toml", "prettier.config.ts"])
def test_finds_prettier_from_any_config_file(tmp_path, config):
    root = apply("core", tmp_path)
    (root / config).write_text("")
    assert "markdown-formatter" in rules(root)


def test_finds_prettier_as_a_dependency_however_package_json_is_spaced(tmp_path):
    root = apply("core", tmp_path)
    (root / "package.json").write_text('{"devDependencies": {"prettier" : "^3.0.0"}}')
    assert "markdown-formatter" in rules(root)


def test_core_repo_without_prettier_is_left_alone(tmp_path):
    root = apply("core", tmp_path)
    (root / "package.json").write_text('{"devDependencies": {"eslint": "^9.0.0"}}')
    assert "markdown-formatter" not in rules(root)


def test_catches_a_uv_project_on_the_pip_ecosystem(tmp_path):
    root = apply("python", tmp_path)
    (root / "uv.lock").write_text("version = 1\n")
    assert "dependabot-uv" in rules(root)


def test_uv_project_on_the_uv_ecosystem_passes(tmp_path):
    root = apply("python", tmp_path)
    (root / "uv.lock").write_text("version = 1\n")
    path = root / ".github/dependabot.yml"
    path.write_text(path.read_text().replace("package-ecosystem: pip", "package-ecosystem: uv"))
    assert "dependabot-uv" not in rules(root)


def test_python_ci_runs_every_tool_through_the_chosen_installer():
    # Each job detects uv.lock, installs uv only then, and runs ruff and pytest
    # behind $RUN, which is `uv run --locked` with a lock and empty without.
    workflow = yaml.safe_load((ROOT / ".github/workflows/python-ci.yml").read_text())
    for job_id, job in workflow["jobs"].items():
        steps = job["steps"]
        names = [s.get("name") for s in steps]
        assert "Use uv if the repo has a lockfile" in names, job_id
        uv = [s for s in steps if str(s.get("uses", "")).startswith("astral-sh/setup-uv@")]
        assert len(uv) == 1 and uv[0]["if"] == "steps.tool.outputs.uv == 'true'", job_id
        for step in steps:
            command = str(step.get("run", ""))
            if command.split()[:1] in (["ruff"], ["pytest"]):
                raise AssertionError(f"{job_id}: {command!r} bypasses $RUN")
        install = next(st for st in steps if st.get("name") == "Install")
        assert "uv sync --locked $UV_SYNC_ARGS" in install["run"], job_id


def test_uv_tools_run_in_the_synced_environment():
    # `uv run` without --no-sync would sync again with uv's defaults, which
    # leaves out the extras `uv-sync-args` installed.
    text = (ROOT / ".github/workflows/python-ci.yml").read_text()
    assert text.count('echo "RUN=uv run --no-sync"') == 3
    workflow = yaml.safe_load(text)
    assert workflow[True]["workflow_call"]["inputs"]["uv-sync-args"]["default"] == "--all-extras"


def test_catches_a_uv_entry_that_misses_the_root_lock(tmp_path):
    root = apply("python", tmp_path)
    (root / "uv.lock").write_text("version = 1\n")
    path = root / ".github/dependabot.yml"
    path.write_text(path.read_text().replace(
        "  - package-ecosystem: github-actions",
        "  - package-ecosystem: uv\n    directory: /tools\n    schedule:\n      interval: weekly\n"
        "    commit-message:\n      prefix: chore\n      prefix-development: chore\n"
        "  - package-ecosystem: github-actions",
    ))
    assert "dependabot-uv" in rules(root)
