# github-boilerplate

[![GitHub release](https://img.shields.io/github/v/release/atdr/github-boilerplate?include_prereleases)](https://github.com/atdr/github-boilerplate/releases)
[![GitHub last commit](https://img.shields.io/github/last-commit/atdr/github-boilerplate)](https://github.com/atdr/github-boilerplate/commits/main)
[![CI](https://github.com/atdr/github-boilerplate/actions/workflows/ci.yml/badge.svg)](https://github.com/atdr/github-boilerplate/actions/workflows/ci.yml)

Reusable GitHub Actions workflows, a repository template and the scripts that
apply them: the setup shared by atdr's repositories, written down once.
[STANDARDS.md](STANDARDS.md) explains every decision.

Pre-release. Expect breaking changes between minor versions until 1.0.

## What you get

- **Reusable workflows**, pinned by tag: Node and Python CI, Markdown lint,
  conventional commit and PR title checks, and a conventions check.
- **A template**: a shared core (issue and PR templates, Dependabot,
  `SECURITY.md`, `AGENTS.md`, lint settings, caller workflows) plus an overlay
  for Node, Python or TeX.
- **Repository settings** as code: squash only merges, security features and a
  branch ruleset that requires the CI gates.

## Usage

Copy the template into a repo, new or existing:

```bash
scripts/apply.sh node ~/dev/my-package
```

Files already in the target are left alone and listed, so you can compare them
by hand. `--force` overwrites them.

Then apply the repository settings. It prints what it would change until you
pass `--apply`:

```bash
scripts/configure.sh atdr/my-package node
scripts/configure.sh atdr/my-package node --apply
```

Or call a reusable workflow directly:

```yaml
jobs:
  node:
    uses: atdr/github-boilerplate/.github/workflows/node-ci.yml@v0.1.0
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

Dependabot's `github-actions` entry proposes each new tag as a PR.

## Development

See [AGENTS.md](AGENTS.md#commands).

## License

[MIT](LICENSE)
