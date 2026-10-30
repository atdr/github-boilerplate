#!/usr/bin/env bash
# Applies the repository settings in STANDARDS.md to a GitHub repo: merge
# rules, security features, the default workflow token, the main ruleset, and
# the deployment environments its workflows publish from.
#
# Usage: scripts/configure.sh <owner/repo> [--apply|--diff]
#
# What a repo needs is read from its own workflows, not from which overlay it
# was built from: each gate where it has that gate's workflow, Actions may open
# PRs where it runs release-please, and only the publishing environments it
# names.
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
	echo "usage: $0 <owner/repo> [--apply|--diff]" >&2
	exit 2
}

[ $# -ge 1 ] || usage
repo=$1
mode=${2:-}
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
#
# Any doubt aborts rather than guessing: a wrong `false` here would make
# --apply switch the permission off in a repo whose releases need it.
uses_release_please=false
workflow_settings=$(mktemp)
api_error=$(mktemp)
trap 'rm -f "$workflow_settings" "$api_error"' EXIT
# Only a 404 means the repo has no workflows folder. gh prints that error body
# to stdout, so the output only counts when the call succeeded.
if ! workflows=$(gh api "repos/$repo/contents/.github/workflows" --jq '.[].path' 2>"$api_error"); then
	if grep 'HTTP 404' "$api_error" >/dev/null; then
		workflows=
	else
		echo "could not list $repo's workflows:" >&2
		cat "$api_error" >&2
		exit 1
	fi
fi
for path in $workflows; do
	if ! content=$(gh api "repos/$repo/contents/$path" --jq .content); then
		echo "could not read $path in $repo" >&2
		exit 1
	fi
	# Decoded whole and matched with case, not piped into grep -q: under
	# pipefail an early grep exit can SIGPIPE the decoder and read as no match.
	decoded=$(printf '%s' "$content" | base64 --decode)
	all_workflows="${all_workflows:-}$decoded
"
done
case "${all_workflows:-}" in
*googleapis/release-please-action*) uses_release_please=true ;;
esac
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

	# A gate is required only where the repo has the workflow that reports it:
	# `<stem> gate` comes from .github/workflows/<stem>.yml, and a ruleset
	# requiring a check no workflow reports would block every merge. A repo
	# with none (a template whose workflows must also run in the repos made
	# from it) keeps the rest of the ruleset. scripts/ruleset.jq does the cut.
	gates=
	for stem in pull-request checks ci; do
		case "
$workflows
" in
		*"
.github/workflows/$stem.yml
"*) gates="$gates$stem gate
" ;;
		esac
	done
	ruleset=$(jq -c --arg gates "$gates" -f "$here/scripts/ruleset.jq" "$settings/ruleset-main.json")
	if [ -n "$gates" ]; then
		echo "requires: $(printf '%s' "$gates" | paste -sd, - | sed 's/,/, /g')"
	else
		echo "requires no status checks: none of pull-request.yml, checks.yml, ci.yml"
	fi
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
# cannot mint the publishing token. Only the ones the repo's workflows name:
# a repo that publishes nowhere gets none.
environment() {
	local name=$1 limit=$2
	if [ "$limit" = main ]; then
		run gh api -X PUT "repos/$repo/environments/$name" --silent --input - <<'JSON'
{"deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
JSON
		# Captured, then matched: no grep -q at the end of a pipeline, which
		# under pipefail can read a match as a miss.
		policies=$(gh api "repos/$repo/environments/$name/deployment-branch-policies" \
			--jq '.branch_policies[].name' 2>/dev/null) || policies=
		case "
$policies
" in
		*"
main
"*) ;;
		*)
			run gh api -X POST "repos/$repo/environments/$name/deployment-branch-policies" \
				--silent -f name=main -f type=branch
			;;
		esac
	else
		run gh api -X PUT "repos/$repo/environments/$name" --silent
	fi
}

# Every environment the workflows' jobs name, in any form a job can declare it
# (see the awk program). Matched as whole lines below, so npm-release never
# matches npm-prerelease.
environments=$(printf '%s\n' "${all_workflows:-}" | awk -f "$here/scripts/workflow-environments.awk")
names_environment() {
	case "
$environments
" in
	*"
$1
"*) return 0 ;;
	esac
	return 1
}

if names_environment npm-release; then
	environment npm-release main
	echo "then on npmjs.com: add a trusted publisher for publish-release.yml" \
		"(environment npm-release)"
fi
if names_environment npm-prerelease; then
	# Dispatched by hand from any branch a beta is built from.
	environment npm-prerelease any
	echo "then on npmjs.com: add a trusted publisher for publish-prerelease.yml" \
		"(environment npm-prerelease)"
fi
if names_environment pypi; then
	environment pypi main
	echo "then on pypi.org: add a trusted publisher for release-please.yml" \
		"(environment pypi)"
fi

echo "and add the CODECOV_TOKEN secret if the repo reports coverage"
[ "$mode" = --apply ] || echo "dry run: nothing changed. Rerun with --apply."
