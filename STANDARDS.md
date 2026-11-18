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

**Pinning:** callers pin an exact tag (`@v1.2.3`), and Dependabot opens a PR for
each release, so every change runs through each caller's own CI before it lands
there. There is no moving `v1` tag: one would carry an unreviewed change to
every repo at once, and the template pins and the conventions fetch
(`job.workflow_sha`) are built around exact tags anyway.

**Versions** follow semver. A release is major when it can turn a caller that
passed before red, or needs the caller to change: a reusable workflow input,
secret or job name removed or renamed, a gate renamed, or a new rule in
`check-conventions.py` that a compliant repo can fail (0.4.0's Codecov rule
would be one). A new check that passes for every repo already following these
standards, or a new optional input, is minor. Each breaking change says what
callers must do in its `BREAKING CHANGE:` footer, which release-please carries
into the changelog.

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
  broke it. That needs a group per run outside pull requests (`github.run_id`),
  not just `cancel-in-progress: false`: GitHub keeps one pending run per group,
  so in a shared group a third push drops the second push's run before it
  starts.
- **Release, publish, deploy, and scheduled jobs that write:** a fixed group
  with `cancel-in-progress: false`, so runs queue. GitHub keeps only one pending
  run per group and replaces it with a newer one, which is fine when the newer
  run covers the older (a release from `main`). Where each run is distinct (a
  prerelease of a given version, a manual run), key the group by it. A publish
  cancelled halfway can leave a tag with no package.
- **PR only workflows** (title checks) may cancel unconditionally.

### Gates

Each caller workflow ends in one gate job (`ci gate`, `checks gate`,
`pull-request gate`) that `needs:` every other job and fails if any failed or
was cancelled. Branch protection requires the gates and nothing else.

A gate runs `if: ${{ !cancelled() }}`, not `always()`. A run superseded by a
newer one is cancelled, and with `always()` its gate would still report a
failure on the same commit the newer run is checking.

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
- **Lockfiles:** an application, which runs its own code (a scheduled scrape, a
  deploy), pins its dependencies with a lockfile, so a new upstream release only
  reaches it through a tested Dependabot PR and a release. A library does not:
  its users resolve their own versions. In Python, a `uv.lock` makes `python-ci`
  install with `uv sync --locked`, and Dependabot then uses the `uv` ecosystem
  [dependabot-uv].
- **Coverage reports, it does not gate** [codecov]. A separate job re-runs the
  suite under coverage on one version. The coverage run itself must pass; the
  Codecov upload is `continue-on-error`. Both statuses in `codecov.yml` report
  their real result. `patch` targets 100%, so a PR adding untested lines shows a
  red patch status, and `project` sets a small `threshold` so rounding stays
  green. They are never `informational`, which always passes and hides exactly
  that. What keeps them from blocking a merge is the ruleset, which requires the
  gates and nothing else.
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

- Runs on push to `main` and daily. Inline `release-type` until the repo needs a
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
in an environment (`npm-release`, `pypi`) limited to `main`, and sets the
environment's `url` to the version it published, so each deployment on the
environment's page links to its release on the registry. Where a service has no
OIDC (Cloudflare), the token is an environment secret limited to `main`, and the
deploy job cannot write to the repo. An optional deploy is switched on by a
repository variable, because a job-level `if:` can read `vars` but not
`secrets`.

## Dependabot

- **Always a `github-actions` entry** [dependabot]. Major-tag pins (`@v7`)
  absorb minor and patch releases but never cross a major. It also bumps the
  exact-tag pins on this repo's reusable workflows. Those pins are grouped:
  Dependabot counts each workflow file as its own dependency, and ungrouped one
  release would open a PR per file.
- **Prefixes are chosen for release-please** [dependabot-prefix]. A runtime
  dependency bump changes what users install, so it is `fix` and cuts a release.
  Development bumps are `chore` and release-silent. Actions bumps are `ci`. A
  package with no runtime dependencies uses `chore(deps)` for both: Dependabot
  misfiles some transitive dev dependencies as production.
- **Group development minor and patch updates.** Production updates stay
  ungrouped, one reviewable PR each.
- **Patch and minor bumps auto-merge.** `auto-merge.yml` switches on GitHub's
  auto-merge for them, so each lands once every required check passes; majors
  wait for review, and a grouped PR that gains a major after auto-merge was on
  has it switched off again. Every ecosystem has a three day cooldown first, so
  a compromised release can be pulled before it merges itself. Auto-merge is on
  only where the ruleset requires at least one gate, and only for PRs into the
  default branch, the one branch the ruleset covers: with nothing required it
  merges at once. `configure.sh` switches it on after the ruleset is in place. A
  merge made this way is pushed by `GITHUB_TOKEN`, which starts no `push`
  workflow, so CI on `main` and deploys next run on the following push.
  release-please also runs daily, so its release PR opens within a day of the
  bump. GitHub disables scheduled workflows in a public repo with no activity
  for 60 days. CodeQL's default setup is not a workflow and still scans `main`
  within minutes of the merge.
- **CodeQL is not a gate.** Default setup analyzes some Dependabot PRs and skips
  others, reporting a neutral "configurations not found" with no analysis, and a
  ruleset that requires code scanning results blocks a merge whose results never
  arrive. A dependency bump changes manifests and lock files, not the source
  CodeQL reads. Dependabot alerts and the cooldown cover it, plus the dependency
  audit, which blocks `ci gate` on a production advisory: `node-ci`'s
  `npm audit` and `python-ci`'s `pip-audit` (see the table below). Any CodeQL
  alert still surfaces from the scan of `main`.
- **Adding auto-merge to a repo: settings first.** Run `configure.sh --apply`
  before merging the PR that adds `auto-merge.yml`. That merge changes
  `dependabot.yml`'s pins, Dependabot opens PRs within seconds, and a job that
  finds the repo setting still off leaves its PR for review, with nothing to run
  it again. The setting does nothing until the workflow asks for it.
- **Never group security updates** [dependabot-security-group]. In philipsair a
  security group filtered a high advisory out of its own job and still reported
  success, so the alert sat open with nothing to show for it.

## Copilot auto-merge (pilot)

In this repo only, and not yet a reusable workflow: an owner PR that Copilot
approved merges itself once every gate the ruleset requires passes.
`copilot-auto-merge.yml` merges it, and the ruleset refuses the merge until the
gates are green and every review thread is resolved, so a Copilot review with
comments blocks it. The ruleset asks Copilot for a review on each PR and on
every push to it.

- **Whose PRs.** Only the owner's, from a branch in this repo: never a fork,
  never Dependabot (its own auto-merge above covers it), and never a
  release-please PR, so the release stays a human checkpoint before any caller
  picks a change up. A draft is left alone, which is how to hold one back.
- **Only the commit Copilot approved.** The merge goes ahead only while
  Copilot's latest review is an approval of the PR's current head, and once
  GitHub reports the PR mergeable. It names that commit (`--match-head-commit`),
  so GitHub refuses it if a push has moved the head. Not GitHub's auto-merge:
  that stays on across pushes, so a push Copilot never saw could merge if its
  checks passed before anything switched it off.
- **No `pull_request_review` trigger.** GitHub holds a run started by Copilot's
  review for manual approval before any job is read, reportedly starts none for
  an approval without inline comments, and would run the PR's own copy of the
  workflow with a write token. So a sweep every ten minutes merges what is
  ready. It runs the copy on the default branch, so a PR, including the one that
  changes the workflow, never runs its own version, and it has no
  `workflow_dispatch`, since a manual run can pick a PR branch's copy. Nothing
  from a PR is checked out or run.
- **CI on `main` still runs.** A merge made with `GITHUB_TOKEN` starts no `push`
  workflow, so after each merge the sweep dispatches `ci` and `checks` on the
  default branch, which that token may do. A dispatch runs on the branch tip, so
  if another merge lands before either dispatch the sweep fails with a warning
  naming the commit left without runs of its own; the tip's runs still cover the
  combined result.
- **Risk accepted.** A change can be written by an agent, approved by Copilot
  and merged with no human reading it. The release PR is then the only
  checkpoint before the change reaches caller repos. On its first five PRs here
  Copilot approved every one with no comments, so it is a light filter.

**Extend it** to other repos, as a reusable workflow, once it has merged at
least ten PRs here with no change reverted or fixed afterwards for something a
reviewer should have caught, and with no push after an approval ever seen to
merge. **End it** on the first change that reaches a release PR broken in a way
a reading would have caught, or if Copilot reviews stop arriving reliably:
delete the workflow and drop the ruleset's Copilot review rule.

## Repository settings

Tracked as data in `settings/` and applied by `scripts/configure.sh`;
`configure.sh <repo> --diff` reports where a repo has drifted from them.

Actions may create PRs only in a repo that runs release-please, which opens its
release PR with `GITHUB_TOKEN`. New repos default this off, and release-please
then fails after pushing its branch. Everywhere else it stays off, so no
workflow can open or approve a PR it was not built to.

| Setting                             | Value                      |
| ----------------------------------- | -------------------------- |
| Merge methods                       | Squash only                |
| Squash commit title / message       | PR title / commit messages |
| Delete branch on merge              | On                         |
| Auto-merge                          | Where a gate is required   |
| Default workflow token              | Read                       |
| Actions may create PRs              | Only with release-please   |
| Dependabot alerts, security updates | On                         |
| Secret scanning, push protection    | On (public repos)          |
| Private vulnerability reporting     | On (public repos)          |
| CodeQL default setup                | On (public repos)          |
| Ruleset `main`                      | See below (public repos)   |

The ruleset (`settings/ruleset-main.json`) blocks deletion and force pushes,
requires linear history, a PR with resolved conversations and squash merge, and
the gates. No bypass actors, so it binds admins too. Zero required approvals:
these are solo repos. Where the repo runs the Copilot auto-merge pilot, it also
asks Copilot to review each PR and every push to it, which reaches only authors
with Copilot code review, so not Dependabot or release-please. Elsewhere the
rule is dropped, since nothing acts on those reviews. A Copilot approval counts
toward required approvals only where a Copilot setting allows it, and even then
a count of one would leave those two waiting for an approval that never comes.

The exception is a repo whose owner commits straight to the default branch on
purpose, such as a link list where each change is one validated line and a PR
adds ceremony without safety. It commits `.github/admin-bypass`, a file whose
comment says why, and the ruleset then lets the repository admin role bypass it.
Everyone else, Dependabot included, still merges through a gated PR, so the repo
keeps its gates for the changes that need them. The file, not a flag to
`configure.sh`, records the choice, so rerunning `--apply` keeps it.

Only the gates a repo's workflows report are required: a required check that
never reports blocks every merge. A repo that keeps its own workflows instead of
the boilerplate's, such as a template whose workflows must also run in the repos
made from it, gets the rest of the ruleset with no required checks.

The gates need not have run against the latest `main`. Requiring that makes
every open PR, release-please's included, merge `main` in and rerun CI each time
another PR lands, and in a solo repo two PRs rarely collide in a way the gates
would catch. CI on `main` after the merge still does. "Update branch" stays
available for when it is wanted.

**The ruleset replaces classic branch protection.** GitHub enforces both, so
protection left over from before a repo adopted the gates still requires the
check names its old workflows reported, and blocks every merge once those checks
are gone. `--diff` reports it as drift. `--apply` warns and prints the command
that removes it, but leaves it in place, since it can hold settings the ruleset
does not.

**The publishing environments' branch policy is the only guard.** The publish
workflows add no branch check of their own, so `npm-release` and `pypi` must
allow exactly one branch policy, `branch:main`. `--diff` reports either one as
drift where it is missing, open to any branch or protected branches, or allows
anything besides `main`; `npm-prerelease`, dispatched from any branch on
purpose, only where it is missing. `--apply` deletes every other branch policy
on the two, naming each one, since a branch added in the UI could otherwise mint
the publishing token.

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

markdownlint-cli2 and mdformat, both run by `markdown.yml`. mdformat owns
Markdown formatting: a Node repo lists `*.md` in `.prettierignore`, because
Prettier formats it differently and the two would undo each other
[markdown-formatter]. Prose wraps at 80 columns; tables and code blocks are
exempt. mdformat rewraps paragraphs, so editing a sentence never means
rewrapping by hand. `CHANGELOG.md` (generated) and `CLAUDE.md` (a symlink) are
excluded.

This applies to committed `.md` files only. Prose posted to GitHub (issues, PRs,
comments) is never hard wrapped: GitHub renders each newline as a line break.

## Ecosystem specifics

| Topic       | Node                            | Python                             | TeX                                  |
| ----------- | ------------------------------- | ---------------------------------- | ------------------------------------ |
| Local hooks | husky                           | pre-commit                         | pre-commit                           |
| Formatter   | Prettier, `printWidth: 100`     | ruff format                        | tex-fmt                              |
| Audit       | `npm audit`, prod blocking      | `pip-audit`, runtime blocking      | n/a                                  |
| Release     | release-please `node`, npm OIDC | release-please `python`, PyPI OIDC | build releases from atdr/latex-build |
