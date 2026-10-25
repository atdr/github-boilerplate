# __REPO__

<!-- Stable instructions only. TODOs, status and changelogs do not belong here:
they change too often and cost context on every session. The backlog is GitHub
Issues; the record of what happened is git history and CHANGELOG.md. -->

One paragraph: what this is, who uses it, and how it is delivered.

## Commands

```bash
# install, lint, format, test, coverage: the exact commands CI runs
```

## Architecture

The main modules, what each owns, and how data flows between them.

## Conventions

- **Git workflow:** GitHub Flow. Every change lands on a `<type>/<description>`
  branch and merges by squash PR. Never commit directly to `main`.
- **Commits and PR titles:** Conventional Commits, `<type>(<scope>): <summary>`,
  with types `feat fix perf refactor test docs chore ci`. The PR title becomes
  the commit on `main`, which release-please reads.
- **Releases:** automated by release-please. Never bump the version or edit
  CHANGELOG.md by hand.
- **Workflows:** each file's `name:` is its filename stem, and every job sets
  `timeout-minutes`. See atdr/github-boilerplate's STANDARDS.md.

## Gotchas

The things most likely to bite someone new to this code.
