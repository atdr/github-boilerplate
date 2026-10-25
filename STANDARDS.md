# Standards

How a repository built from this boilerplate is set up, and why. Distilled from
atdr/contrail, atdr/contrail-gh, atdr/homebridge-philipsair-platform and
atdr/buzz-me-in, with atdr/latex-build and atdr/capsule-caffeine for coverage of
other ecosystems.

Each section gives the rule, the reason, and the exceptions. Where
`scripts/check-conventions.py` enforces a rule, its rule id is in brackets; the
check runs in every repo through `conventions.yml`.

## Layout

The template has a shared core and one overlay per ecosystem.

| Directory         | What it adds                                                  |
| ----------------- | ------------------------------------------------------------- |
| `template/core`   | Everything every repo gets: settings files, templates, checks |
| `template/node`   | npm CI, npm publishing, husky and commitlint, Prettier        |
| `template/python` | pytest and ruff CI, PyPI publishing, pre-commit               |
| `template/tex`    | The atdr/latex-build workflow, tex-fmt, pre-commit            |

Rule of thumb for where something goes: if it depends on the language's package
manager or toolchain, it is an overlay. Otherwise it is core, and is decided
once.

## Workflows

### Reusable workflows, pinned to exact tags

CI logic lives in this repo's reusable workflows (`node-ci.yml`,
`python-ci.yml`, `markdown.yml`, `conventions.yml`, `conventional.yml`). A
repo's own workflow files are thin callers.

**Why:** a fix lands in one place, and reaches every repo as a Dependabot PR.
Copied workflows drift: buzz-me-in and philipsair started from the same CI and
ended up with different Node matrices, timeouts and audit handling.

**Pinning:** callers pin an exact tag (`@v0.3.1`). While this repo is pre-1.0 a
breaking change bumps the minor version, so a moving `v0` tag would carry
breaking changes to every caller. At 1.0 a moving `v1` tag can follow
atdr/latex-build's pattern.

**Exception:** publishing stays in the caller's own file. npm's and PyPI's
trusted publishers name the workflow file that publishes, and that has to be the
caller's.

### Naming [workflow-name]

Each workflow's top-level `name:` is its filename stem (`ci`, `checks`,
`publish-release`). The job's `name:` says what it does. Matrix jobs interpolate
the version (`node ${{ matrix.node-version }}`).

**Why:** GitHub labels a check `<workflow> / <job>` and never shows the
filename. With the name equal to the stem, every check maps back to its file
without guessing. A matrix job with a static name produces several checks with
the same label.

### Timeouts [job-timeout]

Every job sets `timeout-minutes`: 10 by default, 5 for title and gate checks,
more only for real work (a TeX Live install, a Claude session).

**Why:** GitHub's default is six hours, and the failure that matters is a stall,
not an error. A `pip`, `npm` or `npx` fetch that hangs never fails on its own.
contrail once had an `npx` fetch that sat silent for exactly 301 seconds, often
enough to dominate the job.

**Exception:** a job that calls a reusable workflow (`uses:`) takes no timeout
of its own; the called workflow's jobs carry it.

### Permissions [workflow-permissions]

Top-level `permissions:` is `contents: read`, or `{}` where every job states its
own. Jobs widen it only for what they do. A publishing job never holds a
writable `contents` token.

### Concurrency [concurrency]

- **CI:** cancel superseded runs on pull requests only:
  `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. On `main`
  every commit keeps its own result, so a red run points at the commit that
  broke it.
- **Release, publish, deploy, and scheduled jobs that write:** a fixed group
  with `cancel-in-progress: false`, so runs queue. A publish cancelled halfway
  can leave a tag with no package.
- **PR only workflows** (title checks) may cancel unconditionally.

### Gates

Each caller workflow ends in one gate job (`ci gate`, `checks gate`,
`pull-request gate`) that `needs:` every other job and fails if any failed or
was cancelled. Branch protection requires the gates and nothing else.

**Why:** the Node matrix follows LTS, so its job names change when a line enters
or leaves LTS. Requiring those names would break the ruleset each time, and
requiring jobs inside another repository's reusable workflow ties the ruleset to
names it does not control.

### Required checks must actually run

Absence of a check is not a passing check. A run held for approval (the release
PR's, see below) produces no check runs, and `gh pr checks` then exits 0. Before
merging, confirm each gate reported.

## Testing and coverage

- **Versions:** Node follows every line currently in LTS, read from the Node
  release schedule at run time. Python takes an explicit list matching
  `requires-python`.
- **Coverage reports, it does not gate** [codecov]. A separate job re-runs the
  suite under coverage on one version. The coverage run itself must pass; the
  Codecov upload is `continue-on-error`, and both statuses in `codecov.yml` are
  `informational`.
- **Coverage scope lives in project config** (`pyproject.toml`, the `coverage`
  npm script), not on the CI command line, so running it locally measures what
  CI measures.
- **Audits run in their own job.** An advisory reflects the database at a point
  in time, not the diff, so it must not look like the PR broke something.
  Production dependencies block. Development dependencies report an `::error`
  annotation on a green job: louder than a warning, and unlike
  `continue-on-error` it explains itself.

## Config guard tests

A rule written only in prose drifts. Every rule above that a machine can check
is checked: generic ones by `conventions.yml`, repo-specific ones by the repo's
own test suite (philipsair's test that fails when a runtime dependency appears
while Dependabot's prefix still says `chore`, for example).

## Commits, PRs and releases

### One commit type list [commit-types]

`feat fix perf refactor test docs chore ci`, everywhere: commitlint, the
pre-commit hook, the PR title check. `conventional.yml` holds the list;
`check-conventions.py` holds the same list and fails any config that disagrees.

**Why:** philipsair and buzz-me-in both left out `perf`, which release-please
shows in the changelog. `config-conventional`'s own default allows `build`,
`style` and `revert`, so a config must set `type-enum` explicitly.

### Linted twice

- **PR title** (`amannn/action-semantic-pull-request`): on a squash merge the
  title becomes the commit on `main`, which release-please reads. An
  unconventional title silently drops the change from the changelog.
- **Every commit** (`wagoid/commitlint-github-action`, config generated from the
  type list, so non-Node repos need no commitlint config). Locally: husky in
  Node repos, pre-commit's `commit-msg` stage elsewhere.
- Dependabot's commits are exempt: their bodies embed URLs too long to wrap.
- The title check uses `pull_request`, not `pull_request_target`. Events caused
  by `GITHUB_TOKEN` start no `pull_request_target` run, so the check never
  reports on the release PR, which then cannot merge.

### release-please

- Runs on push to `main`. Inline `release-type` until the repo needs a
  `release-please-config.json` (extra-files, pre-1.0 bump rules, several
  packages) [release-please: the config and manifest come as a pair].
- Publishing is a later job in the same workflow, gated on `release_created`. A
  release made with `GITHUB_TOKEN` starts no `on: release` workflow.
- The release PR's own runs are created but held for "Approve and run". Approve
  them, or the required gates never report.
- Never bump a version or edit `CHANGELOG.md` by hand.
- npm prereleases publish from a manual `publish-prerelease.yml`: the bump is
  runner-local, the dist-tag is never `latest`, and the commit gets a
  `prerelease/X.Y.Z-beta.N` tag, never a GitHub Release (release-please would
  read it as the last release).

### Publishing

OIDC trusted publishing to npm and PyPI. No stored tokens. Each publish job runs
in an environment (`npm-release`, `pypi`) limited to `main`. Where a service has
no OIDC (Cloudflare), the token is an environment secret limited to `main`, and
the deploy job cannot write to the repo. An optional deploy is switched on by a
repository variable, because a job-level `if:` can read `vars` but not
`secrets`.

## Dependabot

- **Always a `github-actions` entry** [dependabot]. Major-tag pins (`@v7`)
  absorb minor and patch releases but never cross a major. It also bumps the
  exact-tag pins on this repo's reusable workflows.
- **Prefixes are chosen for release-please** [dependabot-prefix]. A runtime
  dependency bump changes what users install, so it is `fix` and cuts a release.
  Development bumps are `chore` and release-silent. Actions bumps are `ci`. A
  package with no runtime dependencies uses `chore(deps)` for both: Dependabot
  misfiles some transitive dev dependencies as production.
- **Group development minor and patch updates.** Production updates stay
  ungrouped, one reviewable PR each.
- **Never group security updates** [dependabot-security-group]. In philipsair a
  security group filtered a high advisory out of its own job and still reported
  success, so the alert sat open with nothing to show for it.

## Repository settings

Tracked as data in `settings/` and applied by `scripts/configure.sh`;
`configure.sh <repo> <overlay> --diff` reports where a repo has drifted from
them.

Actions may create PRs only in a repo that runs release-please, which opens its
release PR with `GITHUB_TOKEN`. New repos default this off, and release-please
then fails after pushing its branch. Everywhere else it stays off, so no
workflow can open or approve a PR it was not built to.

| Setting                             | Value                      |
| ----------------------------------- | -------------------------- |
| Merge methods                       | Squash only                |
| Squash commit title / message       | PR title / commit messages |
| Delete branch on merge              | On                         |
| Default workflow token              | Read                       |
| Actions may create PRs              | Only with release-please   |
| Dependabot alerts, security updates | On                         |
| Secret scanning, push protection    | On (public repos)          |
| Private vulnerability reporting     | On (public repos)          |
| CodeQL default setup                | On (public repos)          |
| Ruleset `main`                      | See below (public repos)   |

The ruleset (`settings/ruleset-main.json`) blocks deletion and force pushes,
requires linear history, a PR with resolved conversations and squash merge, and
the gates, up to date with `main`. No bypass actors, so it binds admins too.
Zero required approvals: these are solo repos.

**Private repos on GitHub Free** get no rulesets, branch protection, secret
scanning or private vulnerability reporting. `configure.sh` skips them rather
than failing.

## Files every repo has

- **`AGENTS.md`, with `CLAUDE.md` a symlink to it** [agents-md]. One file every
  tool reads. Stable instructions only: commands, architecture, conventions,
  gotchas. No status, TODOs or changelog.
- **`.gitattributes`** with `* text=auto` [gitattributes].
- **`SECURITY.md`** pointing at private vulnerability reporting, and asking
  reporters not to paste real secrets.
- **`.github/pull_request_template.md`**: What changed, Why, Checks, Test plan.
- **Issue forms** in YAML, with blank issues off.
- **`FUNDING.yml`**.
- **README** badges in this order: package, last commit, CI, coverage. All from
  shields.io with `style=flat-square`, lowercase labels except `CI`, and the CI
  badge on `branch=main` so a failing PR does not turn it red. Then install,
  quick start, configuration, development, contributing, license.

## Markdown

markdownlint-cli2 and mdformat, both run by `markdown.yml`. Prose wraps at 80
columns; tables and code blocks are exempt. mdformat rewraps paragraphs, so
editing a sentence never means rewrapping by hand. `CHANGELOG.md` (generated)
and `CLAUDE.md` (a symlink) are excluded.

This applies to committed `.md` files only. Prose posted to GitHub (issues, PRs,
comments) is never hard wrapped: GitHub renders each newline as a line break.

## Ecosystem specifics

| Topic       | Node                            | Python                             | TeX                                  |
| ----------- | ------------------------------- | ---------------------------------- | ------------------------------------ |
| Local hooks | husky                           | pre-commit                         | pre-commit                           |
| Formatter   | Prettier, `printWidth: 100`     | ruff format                        | tex-fmt                              |
| Audit       | `npm audit`, prod blocking      | not yet                            | n/a                                  |
| Release     | release-please `node`, npm OIDC | release-please `python`, PyPI OIDC | build releases from atdr/latex-build |
