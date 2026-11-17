"""The job name detection configure.sh uses to decide which gates to require."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GATES = ("pull-request", "checks", "ci")


def job_names(workflow: str) -> list[str]:
    result = subprocess.run(
        ["awk", "-f", str(ROOT / "scripts/workflow-job-names.awk")],
        input=workflow,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


GATE_WORKFLOWS = [
    path
    for pattern in (".github/workflows", "template/*/.github/workflows")
    for stem in GATES
    for path in sorted(ROOT.glob(f"{pattern}/{stem}.yml"))
]


@pytest.mark.parametrize("path", GATE_WORKFLOWS, ids=lambda p: str(p.relative_to(ROOT)))
def test_real_gate_workflows_report_their_gate(path):
    assert f"{path.stem} gate" in job_names(path.read_text())


def test_this_repo_has_every_gate_workflow_checked():
    assert len(GATE_WORKFLOWS) == 7


def test_crlf_line_endings():
    # Passed as a string, not read from a file: read_text() would turn the
    # CRLF into LF and hide the case. Bytes in and out, since text mode and
    # splitlines() would both drop a stray \r from a printed name.
    workflow = b"jobs:\r\n  gate:\r\n    name: ci gate\r\n    runs-on: ubuntu-latest\r\n"
    result = subprocess.run(
        ["awk", "-f", str(ROOT / "scripts/workflow-job-names.awk")],
        input=workflow,
        check=True,
        capture_output=True,
    )
    assert result.stdout == b"ci gate\n"


def test_ci_without_a_gate_job():
    workflow = """\
name: ci gate
on: push
jobs:
  test:
    name: test
    runs-on: ubuntu-latest
    steps:
      - name: ci gate
        run: echo ok
"""
    assert job_names(workflow) == ["test"]


def test_workflow_and_step_names_do_not_count():
    workflow = """\
name: ci gate
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: ci gate
        run: |
          name: ci gate
      - uses: actions/checkout@v4
        with:
          name: ci gate
"""
    assert job_names(workflow) == []


@pytest.mark.parametrize(
    "value",
    ["ci gate", '"ci gate"', "'ci gate'", "ci gate  # required", '"ci gate" # required'],
)
def test_quoted_and_commented_names(value):
    workflow = f"jobs:\n  gate:\n    name: {value}\n    runs-on: x\n"
    assert job_names(workflow) == ["ci gate"]


def test_name_after_other_properties_and_four_space_indent():
    workflow = """\
jobs:
    gate:
        needs: [test]
        if: always()
        name: ci gate
        steps:
            - name: other
"""
    assert job_names(workflow) == ["ci gate"]


def test_needs_list_at_property_indent_is_not_a_name():
    workflow = """\
jobs:
  gate:
    needs:
    - a
    name: ci gate
"""
    assert job_names(workflow) == ["ci gate"]


def test_several_jobs_and_job_without_name():
    workflow = """\
jobs:
  a:
    name: first
  b:
    runs-on: x
  c:
    name: third
"""
    assert job_names(workflow) == ["first", "third"]


def test_keys_after_jobs_are_ignored():
    workflow = """\
jobs:
  a:
    name: first
concurrency:
  name: not-a-job
"""
    assert job_names(workflow) == ["first"]


def test_a_different_gate_name_does_not_match():
    workflow = "jobs:\n  g:\n    name: ci gate (legacy)\n"
    assert "ci gate" not in job_names(workflow)


@pytest.mark.parametrize(
    "jobs_key,name_key",
    [('"jobs":', '"name":'), ("jobs :", "name :"), ("'jobs':", "'name' :")],
)
def test_quoted_and_spaced_keys(jobs_key, name_key):
    workflow = f"{jobs_key}\n  gate:\n    {name_key} ci gate\n"
    assert job_names(workflow) == ["ci gate"]


def test_a_reusable_workflow_call_reports_no_check_of_its_own_name():
    # Its checks are named `ci gate / <called job>`, so requiring `ci gate`
    # would block every merge.
    workflow = """\
jobs:
  gate:
    name: ci gate
    uses: ./.github/workflows/gate.yml
  other:
    uses: ./.github/workflows/other.yml
    name: other
  plain:
    name: plain
"""
    assert job_names(workflow) == ["plain"]


@pytest.mark.parametrize(
    "job,reason",
    [
        # Folded: the name is `ci gate`, which a line reading cannot see.
        ("  gate:\n    name: >-\n      ci gate\n", "name: is not a one line value"),
        ("  gate:\n    name: |\n      ci gate\n", "name: is not a one line value"),
        ("  gate:\n    name:\n      ci gate\n", "name: is not a one line value"),
        # A plain scalar continued: the name is `ci gate (legacy)`, not `ci gate`.
        ("  gate:\n    name: ci gate\n      (legacy)\n    runs-on: x\n", "name: spans several lines"),
        ('  gate:\n    name: "ci\n      gate"\n', "name: spans several lines"),
        ("  gate: {name: ci gate, runs-on: x}\n", "not a block mapping"),
        ("  gate: *shared\n", "not a block mapping"),
        ("  gate:\n    <<: *shared\n", "merge key"),
        ("  gate:\n    name: *gate_name\n", "name: is not a one line value"),
    ],
)
def test_unreadable_jobs_are_flagged_not_guessed(job, reason):
    names = job_names(f"jobs:\n{job}")
    assert names == [f"?gate: {reason}"]


def test_jobs_in_flow_style_are_flagged():
    assert job_names("jobs: {gate: {name: ci gate}}\n") == ["?jobs: not a block mapping"]


FAKE_GH = r"""#!/bin/bash
echo "$*" >>"$FAKE/calls"
case "$2" in
repos/example/repo/contents/.github/workflows) echo .github/workflows/ci.yml ;;
repos/example/repo/contents/.github/workflows/ci.yml) base64 <"$FAKE/ci.yml" ;;
*) exit 99 ;;
esac
"""


def test_configure_stops_before_any_change_on_an_unreadable_gate_workflow(tmp_path):
    # --apply against a fake gh that knows only the two read calls: exit 1 with
    # the reason, and no call beyond those reads.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(FAKE_GH)
    (bin_dir / "gh").chmod(0o755)
    (tmp_path / "ci.yml").write_text("jobs:\n  gate:\n    name: >-\n      ci gate\n")
    (tmp_path / "calls").touch()
    result = subprocess.run(
        ["/bin/bash", str(ROOT / "scripts/configure.sh"), "example/repo", "--apply"],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "FAKE": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stderr
    assert 'cannot tell whether .github/workflows/ci.yml has a job named "ci gate"' in result.stderr
    assert "gate: name: is not a one line value" in result.stderr
    assert (tmp_path / "calls").read_text().splitlines() == [
        "api repos/example/repo/contents/.github/workflows --jq .[].path",
        "api repos/example/repo/contents/.github/workflows/ci.yml --jq .content",
    ]


def test_an_unreadable_job_does_not_hide_a_readable_gate():
    workflow = "jobs:\n  odd:\n    name: >-\n      x\n  gate:\n    name: ci gate\n"
    assert job_names(workflow) == ["?odd: name: is not a one line value", "ci gate"]
