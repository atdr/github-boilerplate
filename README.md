# github-boilerplate

[![GitHub release](https://img.shields.io/github/v/release/atdr/github-boilerplate?style=flat-square&label=release)](https://github.com/atdr/github-boilerplate/releases)
[![GitHub last commit](https://img.shields.io/github/last-commit/atdr/github-boilerplate.svg?style=flat-square)](https://github.com/atdr/github-boilerplate)
[![CI](https://img.shields.io/github/actions/workflow/status/atdr/github-boilerplate/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/atdr/github-boilerplate/actions/workflows/ci.yml)

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

Files already in the target are left alone and listed. `--force` overwrites
them, and `--diff` changes nothing but shows how the repo's copies differ from
the template, and which template files it lacks:

```bash
scripts/apply.sh node ~/dev/my-package --diff
```

The caller workflows and configs are copied, not pinned, so a template change
reaches a repo only when you copy it across. Run `--diff` from a checkout of the
release the repo pins, or of the latest, to see what to bring over.

For a new LaTeX document, start from
[atdr/latex-boilerplate](https://github.com/atdr/latex-boilerplate) ("Use this
template"), which holds the document and the local build setup, then run
`scripts/apply.sh tex` on the new repo for the checks it lacks. Files the
document already has are left alone.

Then apply the repository settings. It prints what it would change until you
pass `--apply`:

```bash
scripts/configure.sh atdr/my-package
scripts/configure.sh atdr/my-package --apply
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
