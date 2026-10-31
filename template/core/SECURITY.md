# Security policy

## Supported versions

Only the latest commit on `main`, and the release built from it if the
repository publishes releases, receives security fixes. Older commits and
releases are not patched; the fix lands on `main` and ships in the next release.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public issues.**

Report them privately through GitHub Security Advisories, using the
[Report a vulnerability](https://github.com/__OWNER__/__REPO__/security/advisories/new)
form. That opens a private thread visible only to you and the maintainer.

Please include:

- The release or commit you are running
- What an attacker can do, and what access they need to do it
- Steps to reproduce, or a proof of concept

**Do not include real secrets** (API keys, tokens, private URLs). Describe the
exposure instead; the secret itself is not needed.

You can expect an acknowledgement within a week. If the report is accepted, a
fix and an advisory will follow; if it is declined, you will get the reasoning.
