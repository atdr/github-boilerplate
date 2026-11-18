"""configure.sh checks and enforces the publishing environments' branch policy.

Run against a fake gh that keeps the repo's environments in a JSON file, so an
--apply is visible to the --diff that follows it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "settings"

WORKFLOW = (
    "jobs:\n"
    "  release:\n"
    "    environment: npm-release\n"
    "  beta:\n"
    "    environment:\n"
    "      name: npm-prerelease\n"
    "  python:\n"
    "    environment: pypi\n"
)

# Answers the read calls configure.sh makes, as a public repo with no gate, no
# classic protection and no ruleset, whose merge and Actions settings match
# settings/. Environments live in $FAKE/state.json; every call is logged.
FAKE_GH = r"""#!{python}
import base64, json, os, subprocess, sys

fake = os.environ["FAKE"]
args = sys.argv[2:]
with open(os.path.join(fake, "calls"), "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\n")
method, jq, endpoint, fields, body_from = "GET", None, None, {{}}, None
i = 0
while i < len(args):
    a = args[i]
    if a == "-X":
        method = args[i + 1]; i += 1
    elif a == "--jq":
        jq = args[i + 1]; i += 1
    elif a == "-f":
        k, v = args[i + 1].split("=", 1); fields[k] = v; i += 1
    elif a == "--input":
        body_from = args[i + 1]; i += 1
    elif not a.startswith("-") and endpoint is None:
        endpoint = a
    i += 1
state_path = os.path.join(fake, "state.json")
state = json.load(open(state_path))
envs = state["environments"]
base = "repos/example/repo"

def not_found():
    print('{{"message":"Not Found","status":"404"}}')
    sys.stderr.write("gh: Not Found (HTTP 404)\n")
    sys.exit(1)

def save():
    json.dump(state, open(state_path, "w"))

def out(value):
    text = json.dumps(value)
    if jq is not None:
        text = subprocess.run(["jq", "-r", jq], input=text, text=True,
                              capture_output=True, check=True).stdout
        sys.stdout.write(text)
    else:
        print(text)

rest = endpoint[len(base):] if endpoint.startswith(base) else None
parts = rest.strip("/").split("/") if rest else []
if method == "GET" and rest == "":
    repo = json.load(open({repository!r}))
    repo.update(visibility="public", default_branch="main", allow_auto_merge=False)
    out(repo)
elif method == "GET" and rest == "/contents/.github/workflows":
    out([{{"path": ".github/workflows/publish.yml"}}])
elif method == "GET" and rest == "/contents/.github/workflows/publish.yml":
    out({{"content": base64.b64encode(open(os.path.join(fake, "publish.yml"), "rb").read()).decode()}})
elif method == "GET" and rest == "/actions/permissions/workflow":
    out(json.load(open({workflow!r})))
elif method == "GET" and rest == "/rulesets":
    out([])
elif parts[:1] == ["environments"]:
    name = parts[1]
    env = envs.get(name)
    if len(parts) == 2 and method == "GET":
        if env is None:
            not_found()
        out({{"name": name, "deployment_branch_policy": env["policy"]}})
    elif len(parts) == 2 and method == "PUT":
        env = envs.setdefault(name, {{"policy": None, "branches": []}})
        # gh sends a body only when --input names it.
        if body_from == "-":
            env["policy"] = json.loads(sys.stdin.read())["deployment_branch_policy"]
        save()
    elif len(parts) == 3 and method == "GET":
        if env is None or not (env["policy"] or {{}}).get("custom_branch_policies"):
            not_found()
        out({{"total_count": len(env["branches"]), "branch_policies": env["branches"]}})
    elif len(parts) == 3 and method == "POST":
        if os.path.exists(os.path.join(fake, "post-fails")):
            sys.exit(1)
        new_id = max([b["id"] for b in env["branches"]] + [0]) + 1
        env["branches"].append({{"id": new_id, "name": fields["name"], "type": fields["type"]}})
        save()
    elif len(parts) == 4 and method == "DELETE":
        env["branches"] = [b for b in env["branches"] if str(b["id"]) != parts[3]]
        save()
    else:
        sys.exit(99)
elif method == "GET":
    not_found()
"""

RESTRICTED = {"protected_branches": False, "custom_branch_policies": True}


def main_only(*extra: dict) -> dict:
    return {"policy": RESTRICTED, "branches": [{"id": 1, "name": "main", "type": "branch"}, *extra]}


CLEAN = {
    "npm-release": main_only(),
    "pypi": main_only(),
    "npm-prerelease": {"policy": None, "branches": []},
}


@pytest.fixture
def fake(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(
        FAKE_GH.format(
            python=sys.executable,
            repository=str(SETTINGS / "repository.json"),
            workflow=str(SETTINGS / "actions-workflow.json"),
        )
    )
    gh.chmod(0o755)
    (tmp_path / "publish.yml").write_text(WORKFLOW)
    (tmp_path / "calls").touch()
    return tmp_path


def configure(fake: Path, environments: dict, *args: str, keep: bool = False):
    if not keep:
        (fake / "state.json").write_text(json.dumps({"environments": environments}))
    (fake / "calls").write_text("")
    jq_dir = os.path.dirname(shutil.which("jq") or "/usr/bin/jq")
    result = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts/configure.sh"), "example/repo", *args],
        env={"PATH": f"{fake / 'bin'}:{jq_dir}:/usr/bin:/bin", "FAKE": str(fake)},
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    return result, (fake / "calls").read_text().splitlines()


def test_diff_is_clean_when_each_environment_is_right(fake):
    result, _ = configure(fake, CLEAN, "--diff")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "matches settings/" in result.stdout


@pytest.mark.parametrize(
    ("name", "env", "line"),
    [
        ("npm-release", {"policy": None, "branches": []}, "npm-release: any branch -> branch:main"),
        (
            "npm-release",
            {"policy": {"protected_branches": True, "custom_branch_policies": False}, "branches": []},
            "npm-release: protected branches -> branch:main",
        ),
        ("npm-release", None, "npm-release: missing -> branch:main"),
        (
            "npm-release",
            main_only({"id": 7, "name": "feature/*", "type": "branch"}),
            "npm-release: branch:feature/*, branch:main -> branch:main",
        ),
        ("pypi", {"policy": RESTRICTED, "branches": []}, "pypi: no branch -> branch:main"),
        (
            "pypi",
            {"policy": RESTRICTED, "branches": [{"id": 1, "name": "main", "type": "tag"}]},
            "pypi: tag:main -> branch:main",
        ),
        ("npm-prerelease", None, "npm-prerelease: missing -> any branch"),
    ],
)
def test_diff_reports_an_environment_that_drifted(fake, name, env, line):
    environments = dict(CLEAN)
    if env is None:
        del environments[name]
    else:
        environments[name] = env
    result, _ = configure(fake, environments, "--diff")
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"  environment {line}\n" in result.stdout


def test_diff_leaves_npm_prerelease_open(fake):
    environments = dict(CLEAN)
    environments["npm-prerelease"] = main_only({"id": 5, "name": "beta/*", "type": "branch"})
    result, _ = configure(fake, environments, "--diff")
    assert result.returncode == 0, result.stdout


def test_apply_removes_each_extra_policy_then_diff_is_clean(fake):
    environments = dict(CLEAN)
    environments["npm-release"] = main_only(
        {"id": 7, "name": "feature/*", "type": "branch"},
        {"id": 8, "name": "v*", "type": "tag"},
    )
    result, calls = configure(fake, environments, "--apply")
    assert result.returncode == 0, result.stderr
    assert "npm-release: removes branch policy branch:feature/* (only main may publish)" in result.stdout
    assert "npm-release: removes branch policy tag:v* (only main may publish)" in result.stdout
    deletes = [c for c in calls if c.startswith("api -X DELETE")]
    assert deletes == [
        f"api -X DELETE repos/example/repo/environments/npm-release/deployment-branch-policies/{i} --silent"
        for i in (7, 8)
    ]
    assert not any("-X POST" in c and "deployment-branch-policies" in c for c in calls)
    result, _ = configure(fake, {}, "--diff", keep=True)
    assert result.returncode == 0, result.stdout


def test_apply_restricts_an_open_environment_then_diff_is_clean(fake):
    environments = dict(CLEAN)
    environments["pypi"] = {"policy": None, "branches": []}
    result, _ = configure(fake, environments, "--apply")
    assert result.returncode == 0, result.stderr
    result, _ = configure(fake, {}, "--diff", keep=True)
    assert result.returncode == 0, result.stdout


def test_dry_run_says_what_it_would_remove_and_changes_nothing(fake):
    environments = dict(CLEAN)
    environments["npm-release"] = main_only({"id": 7, "name": "feature/*", "type": "branch"})
    result, calls = configure(fake, environments)
    assert result.returncode == 0, result.stderr
    assert "npm-release: would remove branch policy branch:feature/* (only main may publish)" in result.stdout
    assert (
        "would run: gh api -X DELETE repos/example/repo/environments/npm-release/"
        "deployment-branch-policies/7 --silent"
    ) in result.stdout
    assert not any(c.startswith("api -X") for c in calls)
    result, _ = configure(fake, {}, "--diff", keep=True)
    assert result.returncode == 1
    assert "  environment npm-release: branch:feature/*, branch:main -> branch:main\n" in result.stdout


def test_apply_adds_main_before_removing_anything(fake):
    # A failed add leaves the old policy, so main can still publish.
    environments = dict(CLEAN)
    environments["npm-release"] = {"policy": RESTRICTED, "branches": [{"id": 3, "name": "*", "type": "branch"}]}
    (fake / "post-fails").touch()
    result, calls = configure(fake, environments, "--apply")
    assert result.returncode != 0
    assert (
        "api -X POST repos/example/repo/environments/npm-release/deployment-branch-policies"
        " --silent -f name=main -f type=branch"
    ) in calls
    assert not any(c.startswith("api -X DELETE") for c in calls)
    state = json.loads((fake / "state.json").read_text())
    assert state["environments"]["npm-release"]["branches"] == [{"id": 3, "name": "*", "type": "branch"}]


def test_apply_refuses_a_policy_with_no_type(fake):
    # It could be a tag named main, so it is neither kept nor deleted blindly.
    environments = dict(CLEAN)
    environments["npm-release"] = {"policy": RESTRICTED, "branches": [{"id": 4, "name": "main"}]}
    result, _ = configure(fake, environments, "--diff")
    assert result.returncode == 1
    assert "  environment npm-release: untyped:main -> branch:main\n" in result.stdout
    result, calls = configure(fake, environments, "--apply")
    assert result.returncode == 1
    assert "no type" in result.stderr
    assert not any("deployment-branch-policies" in c and "-X" in c for c in calls)


def test_environment_names_ignore_case(fake):
    # GitHub treats NPM-RELEASE as npm-release.
    (fake / "publish.yml").write_text(WORKFLOW.replace("environment: npm-release", "environment: NPM-Release"))
    environments = dict(CLEAN)
    environments["npm-release"] = {"policy": None, "branches": []}
    result, _ = configure(fake, environments, "--diff")
    assert result.returncode == 1
    assert "  environment npm-release: any branch -> branch:main\n" in result.stdout


def test_an_example_in_a_script_names_no_environment(fake):
    (fake / "publish.yml").write_text(
        "jobs:\n"
        "  docs:\n"
        "    steps:\n"
        "      - run: |\n"
        "          cat <<EOF\n"
        "          environment: npm-release\n"
        "          environment:\n"
        "            name: pypi\n"
        "          EOF\n"
    )
    environments = {"pypi": {"policy": None, "branches": []}}
    result, calls = configure(fake, environments, "--apply")
    assert result.returncode == 0, result.stderr
    assert not any("environments" in c for c in calls)
