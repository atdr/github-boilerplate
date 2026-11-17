"""The Copilot auto-merge pilot's guards (copilot-auto-merge.yml, issue #71):
checked statically, and by running the sweep against a fake `gh`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/copilot-auto-merge.yml"
REPO = "atdr/github-boilerplate"
OWNER = "atdr"
WRITE = {"contents": "write", "pull-requests": "write"}


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text())


def steps(workflow: dict):
    for job in workflow["jobs"].values():
        yield from job["steps"]


def test_triggers_run_only_the_default_branch_copy(workflow):
    # PyYAML reads a bare `on:` as True.
    on = workflow.get("on", workflow.get(True))
    # pull_request_review would run the PR's own copy with a write token.
    assert set(on) == {"schedule", "workflow_dispatch"}


def test_permissions_are_minimal(workflow):
    assert workflow["permissions"] == {}
    for job in workflow["jobs"].values():
        assert job["permissions"] == WRITE


def test_nothing_from_the_pr_is_checked_out_or_run(workflow):
    for step in steps(workflow):
        assert "uses" not in step, "no actions at all, actions/checkout above all"
        assert "${{" not in step["run"], "values reach run through env"
    assert "checkout" not in WORKFLOW.read_text()


def test_merges_directly_never_through_auto_merge(workflow):
    # Auto-merge stays on across pushes, so a push Copilot never saw could
    # merge; a direct merge bound to the approved commit cannot.
    assert set(workflow["jobs"]) == {"sweep"}
    assert "--auto" not in WORKFLOW.read_text()


def test_concurrency_never_cancels(workflow):
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_sweep_guards_are_in_the_script(workflow):
    job = workflow["jobs"]["sweep"]
    (step,) = job["steps"]
    script = step["run"]
    assert step["env"]["OWNER"] == "${{ github.repository_owner }}"
    assert '[ "$author" != "$OWNER" ] || [ "$head_repo" != "$REPO" ]' in script
    assert "release-please--*" in script
    assert "dependabot/*" in script
    assert 'select(.user.login == "copilot-pull-request-reviewer[bot]")' in script
    assert '[ "$latest" = "APPROVED $head_sha" ]' in script
    assert '--match-head-commit "$head_sha"' in script


FAKE_GH = r"""#!/bin/bash
echo "$*" >>"$FAKE/calls"
if [ "$1" = pr ] && [ "$2" = view ]; then
	n=$3
	[ ! -f "$FAKE/view-fail-$n" ] || exit 1
	if [ -f "$FAKE/state-$n" ]; then cat "$FAKE/state-$n"; else echo CLEAN; fi
	exit 0
fi
if [ "$1" = api ]; then
	for arg in "$@"; do
		case "$arg" in
		repos/*/pulls\?*)
			case "$arg" in *"base=main&"*) ;; *) echo "wrong base: $arg" >&2; exit 1 ;; esac
			cat "$FAKE/prs"
			;;
		repos/*/reviews*)
			n=${arg#*/pulls/}
			n=${n%%/*}
			[ ! -f "$FAKE/reviews-fail-$n" ] || exit 1
			[ ! -f "$FAKE/reviews-$n" ] || cat "$FAKE/reviews-$n"
			;;
		"repos/$REPO") echo main ;;
		esac
	done
	exit 0
fi
[ ! -f "$FAKE/fail" ]
"""

HEAD = "a" * 40
OLD = "b" * 40


def pr(number, author=OWNER, head_repo=REPO, ref="feat/x", sha=HEAD, draft=False, enabled_by="-"):
    return "\t".join([str(number), author, head_repo, ref, sha, str(draft).lower(), enabled_by])


def sweep(tmp_path: Path, prs: list[str], reviews: dict[int, list[str]], fail: bool = False,
          states: dict[int, str] | None = None, broken: tuple[str, ...] = ()):
    script = yaml.safe_load(WORKFLOW.read_text())["jobs"]["sweep"]["steps"][0]["run"]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(FAKE_GH)
    (bin_dir / "gh").chmod(0o755)
    (tmp_path / "prs").write_text("".join(f"{line}\n" for line in prs))
    for number, lines in reviews.items():
        (tmp_path / f"reviews-{number}").write_text("".join(f"{line}\n" for line in lines))
    if fail:
        (tmp_path / "fail").touch()
    for number, state in (states or {}).items():
        (tmp_path / f"state-{number}").write_text(f"{state}\n")
    for name in broken:
        (tmp_path / name).touch()
    (tmp_path / "calls").touch()
    (tmp_path / "sweep.sh").write_text(script)
    result = subprocess.run(
        # How GitHub runs a `run:` step on Linux.
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", str(tmp_path / "sweep.sh")],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "FAKE": str(tmp_path), "REPO": REPO,
             "OWNER": OWNER},
        capture_output=True, text=True,
    )
    merges = [c for c in (tmp_path / "calls").read_text().splitlines() if c.startswith("pr merge")]
    return result, merges


def merge(number: int, sha: str = HEAD) -> str:
    return f"pr merge --squash --match-head-commit {sha} --repo {REPO} {number}"


def test_sweep_merges_only_an_approval_of_the_current_head(tmp_path):
    approved = [f"APPROVED {HEAD}"]
    result, merges = sweep(
        tmp_path,
        [
            pr(1),
            pr(2),  # approved an older head
            pr(3),  # approved, then commented on the head
            pr(4, author="someone"),
            pr(5, head_repo="someone/fork"),
            pr(6, head_repo="-"),  # fork since deleted
            pr(7, author="dependabot[bot]", ref="dependabot/npm/x"),
            pr(8, author="github-actions[bot]", ref="release-please--branches--main"),
            pr(9, ref="release-please--branches--main"),
            pr(10, draft=True),
            pr(11, enabled_by=OWNER),  # the owner switched auto-merge on
            pr(12),  # no Copilot review yet
        ],
        {
            1: approved,
            2: [f"APPROVED {OLD}"],
            3: [f"APPROVED {HEAD}", f"COMMENTED {HEAD}"],
            **{n: approved for n in range(4, 12)},
        },
    )
    assert result.returncode == 0, result.stderr
    assert merges == [merge(1)]


def test_sweep_waits_until_github_reports_the_pr_mergeable(tmp_path):
    approved = [f"APPROVED {HEAD}"]
    result, merges = sweep(
        tmp_path,
        [pr(1), pr(2), pr(3), pr(4)],
        {n: approved for n in range(1, 5)},
        states={1: "BLOCKED", 2: "BEHIND", 3: "UNSTABLE", 4: "UNKNOWN"},
    )
    assert result.returncode == 0, result.stderr
    assert merges == [merge(3)]


def test_one_failed_read_does_not_stop_the_sweep(tmp_path):
    approved = [f"APPROVED {HEAD}"]
    result, merges = sweep(
        tmp_path,
        [pr(1), pr(2), pr(3)],
        {n: approved for n in range(1, 4)},
        broken=("reviews-fail-1", "view-fail-2"),
    )
    assert result.returncode == 1
    assert "#1: could not read its reviews" in result.stdout
    assert "#2: could not read its merge state" in result.stdout
    assert merges == [merge(3)]


def test_sweep_fails_visibly_but_tries_every_pr(tmp_path):
    result, merges = sweep(
        tmp_path,
        [pr(1), pr(2)],
        {1: [f"APPROVED {HEAD}"], 2: [f"APPROVED {HEAD}"]},
        fail=True,
    )
    assert result.returncode == 1
    assert merges == [merge(1), merge(2)]


def test_sweep_with_no_open_prs(tmp_path):
    result, merges = sweep(tmp_path, [], {})
    assert result.returncode == 0, result.stderr
    assert merges == []
