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
