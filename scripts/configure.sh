#!/usr/bin/env bash
# Applies the repository settings in STANDARDS.md to a GitHub repo: merge
# rules, security features, the default workflow token, the main ruleset, and
# the deployment environments its overlay publishes from.
#
# Usage: scripts/configure.sh <owner/repo> <node|python|tex|core> [--apply|--diff]
#
# The settings themselves are data in settings/, and STANDARDS.md says why
# each has its value. This script only sends them.
#
# Prints what it would change, and changes nothing, unless --apply is given.
# --diff compares the repo's live merge and Actions settings with settings/.
# Actions may open PRs only in a repo whose workflows run release-please.
# Needs an authenticated gh. Written for bash 3.2 (macOS's stock /bin/bash).

set -euo pipefail

usage() {
	echo "usage: $0 <owner/repo> <node|python|tex|core> [--apply|--diff]" >&2
	exit 2
}

[ $# -ge 2 ] || usage
repo=$1
overlay=$2
mode=${3:-}
case "$overlay" in node | python | tex | core) ;; *) usage ;; esac
[ -z "$mode" ] || [ "$mode" = --apply ] || [ "$mode" = --diff ] || usage

here=$(cd "$(dirname "$0")/.." && pwd)
settings=$here/settings

# Each tracked key whose live value differs, as `key: live -> tracked`.
drift() {
	local endpoint=$1 file=$2
	gh api "$endpoint" | jq -r --slurpfile want "$file" '
		. as $live | $want[0] | to_entries[]
		| select($live[.key] != .value)
		| "  \(.key): \($live[.key]) -> \(.value)"'
}

# A repo running release-please lets Actions open PRs, because release-please
# opens its release PR with GITHUB_TOKEN; every other repo keeps it off.
uses_release_please=false
# A repo with no workflows folder answers 404, and gh prints that error body
# to stdout, so its output only counts when the call succeeded.
workflows=$(gh api "repos/$repo/contents/.github/workflows" --jq '.[].path' 2>/dev/null) || workflows=
for path in $workflows; do
	if gh api "repos/$repo/contents/$path" --jq .content | base64 --decode |
		grep -q 'googleapis/release-please-action'; then
		uses_release_please=true
		break
	fi
done
workflow_settings=$(mktemp)
trap 'rm -f "$workflow_settings"' EXIT
if [ "$uses_release_please" = true ]; then
	jq -s '.[0] * .[1]' "$settings/actions-workflow.json" \
		"$settings/actions-workflow-release-please.json" >"$workflow_settings"
else
	cp "$settings/actions-workflow.json" "$workflow_settings"
fi

if [ "$mode" = --diff ]; then
	# Command substitution drops trailing newlines, so print each part rather
	# than concatenating them.
	repository=$(drift "repos/$repo" "$settings/repository.json")
	workflow=$(drift "repos/$repo/actions/permissions/workflow" "$workflow_settings")
	if [ -n "$repository$workflow" ]; then
		echo "$repo differs from settings/ (live -> tracked):"
		[ -z "$repository" ] || echo "$repository"
		[ -z "$workflow" ] || echo "$workflow"
		exit 1
	fi
	echo "$repo matches settings/ (release-please: $uses_release_please)"
	exit 0
fi

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

run gh api -X PATCH "repos/$repo" --silent --input "$settings/repository.json"
echo "runs release-please: $uses_release_please (Actions may open PRs only if so)"
run gh api -X PUT "repos/$repo/actions/permissions/workflow" --silent \
	--input "$workflow_settings"

run gh api -X PUT "repos/$repo/vulnerability-alerts" --silent
run gh api -X PUT "repos/$repo/automated-security-fixes" --silent

if [ "$visibility" = public ]; then
	run gh api -X PATCH "repos/$repo" --silent --input "$settings/security-public.json"
	run gh api -X PUT "repos/$repo/private-vulnerability-reporting" --silent
	run gh api -X PATCH "repos/$repo/code-scanning/default-setup" --silent \
		-f state=configured

	# Every repo requires the core gates. A repo with a ci.yml (the language
	# overlays, and this boilerplate itself) also requires its ci gate.
	has_ci=false
	if gh api "repos/$repo/contents/.github/workflows/ci.yml" --silent 2>/dev/null; then
		has_ci=true
	fi
	ruleset=$(jq -c --argjson has_ci "$has_ci" '
		if $has_ci then
			(.rules[] | select(.type == "required_status_checks")
				.parameters.required_status_checks) += [{"context": "ci gate", "integration_id": 15368}]
		else . end' "$settings/ruleset-main.json")
	echo "requires: pull-request gate, checks gate$([ "$has_ci" = false ] || echo ', ci gate')"
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
