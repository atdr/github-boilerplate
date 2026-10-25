# github-boilerplate

The standard setup for atdr's repositories: reusable GitHub Actions workflows
that repos pin by tag, a template (shared core plus Node, Python and TeX
overlays) copied into new and existing repos, and the scripts that apply both.
`STANDARDS.md` is the reasoning; everything else is the implementation.

## Commands

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt -r scripts/requirements-conventions.txt \
  -r scripts/requirements-markdown.txt
pytest -q                                   # guards, incl. applying each overlay
python scripts/check-conventions.py .       # this repo against its own rules
actionlint .github/workflows/*.yml template/*/.github/workflows/*.yml
shellcheck scripts/*.sh && shellcheck --shell=sh template/node/.husky/*
npx markdownlint-cli2 && mdformat --check .

scripts/apply.sh <node|python|tex|core> <target-dir> [--force]
scripts/configure.sh <owner/repo> <node|python|tex|core> [--apply]   # dry run by default
```

## Architecture

- `.github/workflows/` holds two kinds of workflow. **Reusable** ones
  (`on: workflow_call`: `conventional`, `node-ci`, `python-ci`, `markdown`,
  `conventions`) run in callers' repos. **This repo's own** (`ci`, `checks`,
  `pull-request`, `release-please`) call the reusable ones locally
  (`uses: ./...`), so a change is exercised here before any caller can pin it.
- `template/core` is copied into every repo, then `template/<overlay>` on top;
  an overlay file replaces the core file at the same path.
- `scripts/check-conventions.py` enforces the checkable rules in `STANDARDS.md`.
  `conventions.yml` fetches it from this repo at the caller's pinned commit
  (`job.workflow_sha`) rather than copying it into each repo.
- `rulesets/main.json` is the branch ruleset; `configure.sh` adds `ci gate` for
  language overlays.

## Conventions

- **Git workflow:** GitHub Flow, `<type>/<description>` branches, squash PRs.
- **Commits and PR titles:** Conventional Commits with types
  `feat fix perf refactor test docs chore ci`. The list lives in
  `conventional.yml` and `check-conventions.py`; `tests/` fails if they
  disagree.
- **Versioning:** release-please, pre-1.0. A breaking change bumps the minor
  version, a `feat` the minor, a `fix` the patch. A change to a reusable
  workflow or to `template/` changes what callers get, so it is `feat` or `fix`,
  never `chore`.
- **Template pins:** every `atdr/github-boilerplate/...@v0.0.0` line in
  `template/` ends in `# x-release-please-version` and its file is listed in
  `release-please-config.json`'s `extra-files`, so the release PR rewrites the
  pins to the version it releases. `apply.sh` strips the marker. A test checks
  both halves.
- **Placeholders:** `__OWNER__` and `__REPO__` in template files, filled by
  `apply.sh`.
- **Scripts** target bash 3.2 (macOS's `/bin/bash`): no `mapfile`, no
  associative arrays.
- Writing: no em dashes; prefer restructuring to hyphenated compounds.

## Gotchas

- PyYAML parses a workflow's bare `on:` key as boolean `True`. Read it as
  `workflow.get("on", workflow.get(True))`.
- A gate's required check name is its job `name:`, and must be unique across all
  workflows in a repo, hence `ci gate`, `checks gate`, `pull-request gate`.
- `.mdformat.toml`'s `exclude` needs Python 3.13 or later.
- Before the first release the manifest says `0.0.0`, and `apply.sh` pins
  callers to `@main` with a warning.
