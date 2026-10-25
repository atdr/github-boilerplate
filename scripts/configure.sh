#!/usr/bin/env bash
# Applies the repository settings in STANDARDS.md to a GitHub repo: merge
# rules, security features, the default workflow token, the main ruleset, and
# the deployment environments its overlay publishes from.
#
# Usage: scripts/configure.sh <owner/repo> <node|python|tex|core> [--apply]
#
# Prints what it would change, and changes nothing, unless --apply is given.
# Needs an authenticated gh. Written for bash 3.2 (macOS's stock /bin/bash).

set -euo pipefail

usage() {
	echo "usage: $0 <owner/repo> <node|python|tex|core> [--apply]" >&2
	exit 2
}

[ $# -ge 2 ] || usage
repo=$1
overlay=$2
mode=${3:-}
case "$overlay" in node | python | tex | core) ;; *) usage ;; esac
[ -z "$mode" ] || [ "$mode" = --apply ] || usage

here=$(cd "$(dirname "$0")/.." && pwd)

run() {
	if [ "$mode" = --apply ]; then
		"$@"
	else
		printf 'would run:'
		printf ' %q' "$@"
		printf '\n'
	fi
}

visibility=$(gh api "repos/$repo" --jq .visibility)
echo "$repo is $visibility"

# Squash only, titled from the PR: the PR title is the commit on main, and
# release-please reads it.
run gh api -X PATCH "repos/$repo" --silent \
	-F allow_squash_merge=true \
	-F allow_merge_commit=false \
	-F allow_rebase_merge=false \
	-F delete_branch_on_merge=true \
	-F allow_update_branch=true \
	-f squash_merge_commit_title=PR_TITLE \
	-f squash_merge_commit_message=COMMIT_MESSAGES

# Read-only by default; workflows widen it per job.
run gh api -X PUT "repos/$repo/actions/permissions/workflow" --silent \
	-f default_workflow_permissions=read

run gh api -X PUT "repos/$repo/vulnerability-alerts" --silent
run gh api -X PUT "repos/$repo/automated-security-fixes" --silent

if [ "$visibility" = public ]; then
	run gh api -X PATCH "repos/$repo" --silent --input - <<'JSON'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"}}}
JSON
	run gh api -X PUT "repos/$repo/private-vulnerability-reporting" --silent
	run gh api -X PATCH "repos/$repo/code-scanning/default-setup" --silent \
		-f state=configured

	# Every repo requires the core gates; a language overlay adds its ci gate.
	ruleset=$(jq -c --arg overlay "$overlay" '
		if $overlay == "node" or $overlay == "python" then
			(.rules[] | select(.type == "required_status_checks")
				.parameters.required_status_checks) += [{"context": "ci gate", "integration_id": 15368}]
		else . end' "$here/rulesets/main.json")
	existing=$(gh api "repos/$repo/rulesets" --jq '.[] | select(.name == "main") | .id')
	if [ -n "$existing" ]; then
		run gh api -X PUT "repos/$repo/rulesets/$existing" --silent --input - <<<"$ruleset"
	else
		run gh api -X POST "repos/$repo/rulesets" --silent --input - <<<"$ruleset"
	fi
else
	# GitHub Free has no rulesets, branch protection, secret scanning or
	# private vulnerability reporting for private repos.
	echo "skipped for a private repo on GitHub Free: secret scanning, private" \
		"vulnerability reporting, code scanning, the main ruleset"
fi

# Publishing environments, limited to main so a workflow on another branch
# cannot mint the publishing token.
environment() {
	local name=$1 limit=$2
	if [ "$limit" = main ]; then
		run gh api -X PUT "repos/$repo/environments/$name" --silent --input - <<'JSON'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
		if ! gh api "repos/$repo/environments/$name/deployment-branch-policies" \
			--jq '.branch_policies[].name' 2>/dev/null | grep -qx main; then
			run gh api -X POST "repos/$repo/environments/$name/deployment-branch-policies" \
				--silent -f name=main -f type=branch
		fi
	else
		run gh api -X PUT "repos/$repo/environments/$name" --silent
	fi
}

case "$overlay" in
node)
	environment npm-release main
	# Dispatched by hand from any branch a beta is built from.
	environment npm-prerelease any
	echo "then on npmjs.com: add trusted publishers for publish-release.yml" \
		"(environment npm-release) and publish-prerelease.yml (npm-prerelease)"
	;;
python)
	environment pypi main
	echo "then on pypi.org: add a trusted publisher for release-please.yml" \
		"(environment pypi)"
	;;
esac

echo "and add the CODECOV_TOKEN secret if the repo reports coverage"
[ "$mode" = --apply ] || echo "dry run: nothing changed. Rerun with --apply."
