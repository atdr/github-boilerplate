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
# --diff compares the repo's live merge and Actions settings with settings/,
# and reports classic branch protection, which the ruleset does not replace.
# Actions may open PRs only in a repo whose workflows run release-please.
# Needs an authenticated gh. Written for bash 3.2 (macOS's stock /bin/bash).

set -euo pipefail

usage() {
	echo "usage: $0 <owner/repo> [--apply|--diff]" >&2
	exit 2
}

# At most one option: --apply --diff together would silently drop --diff and
# change a live repo where a comparison was meant. An empty mode is not a mode.
[ $# -ge 1 ] && [ $# -le 2 ] || usage
repo=$1
mode=${2:-}
[ $# -eq 1 ] || [ "$mode" = --apply ] || [ "$mode" = --diff ] || usage

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
repository_settings=$(mktemp)
api_error=$(mktemp)
protection=$(mktemp)
trap 'rm -f "$workflow_settings" "$repository_settings" "$api_error" "$protection"' EXIT
# Read first: a private repo gets no ruleset, so its gates are never used.
visibility=$(gh api "repos/$repo" --jq .visibility)
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
	# Whether a gate workflow has the job that reports its gate. A job the awk
	# script cannot read for certain prints `?...`; with the gate not found
	# otherwise, stop before changing anything rather than guess either way.
	case "$path" in
	.github/workflows/pull-request.yml | .github/workflows/checks.yml | .github/workflows/ci.yml)
		stem=${path##*/}
		stem=${stem%.yml}
		job_names=$(printf '%s\n' "$decoded" | awk -f "$here/scripts/workflow-job-names.awk")
		case "
$job_names
" in
		*"
$stem gate
"*) gate_jobs="${gate_jobs:-}$stem gate
" ;;
		*"
?"*)
			# Only where the answer is used: a private repo gets no ruleset.
			if [ "$visibility" = public ]; then
				echo "cannot tell whether $path has a job named \"$stem gate\":" >&2
				printf '%s\n' "$job_names" | sed -n 's/^?/  /p' >&2
				echo "Write each job's name: as one line in a block mapping, then rerun." >&2
				exit 1
			fi
			;;
		esac
		;;
	esac
	all_workflows="${all_workflows:-}$decoded
"
done
case "${all_workflows:-}" in
*googleapis/release-please-action*) uses_release_please=true ;;
esac

# A repo whose owner commits straight to the default branch on purpose says so
# by committing .github/admin-bypass; the ruleset then lets the admin role
# bypass it (scripts/ruleset.jq). As above, only a 404 means no.
admin_bypass=false
if gh api "repos/$repo/contents/.github/admin-bypass" --silent 2>"$api_error"; then
	admin_bypass=true
elif ! grep 'HTTP 404' "$api_error" >/dev/null; then
	echo "could not check $repo for .github/admin-bypass:" >&2
	cat "$api_error" >&2
	exit 1
fi
if [ "$uses_release_please" = true ]; then
	jq -s '.[0] * .[1]' "$settings/actions-workflow.json" \
		"$settings/actions-workflow-release-please.json" >"$workflow_settings"
else
	cp "$settings/actions-workflow.json" "$workflow_settings"
fi

# A gate is required only where the repo has the workflow that reports it:
# `<stem> gate` comes from a job named exactly that in
# .github/workflows/<stem>.yml, and a ruleset requiring a check no job reports
# would block every merge. A workflow with that file name but no such job (a
# repo's own ci.yml, say) is reported in $gateless and requires nothing. A repo
# with no gate (a template whose workflows must also run in the repos made from
# it) keeps the rest of the ruleset. scripts/ruleset.jq does the cut.
gates=
gateless=
for stem in pull-request checks ci; do
	case "
${gate_jobs:-}
" in
	*"
$stem gate
"*) gates="$gates$stem gate
" ;;
	*)
		case "
$workflows
" in
		*"
.github/workflows/$stem.yml
"*) gateless="$gateless$stem.yml
" ;;
		esac
		;;
	esac
done

# Auto-merge only where the main ruleset requires at least one gate: with
# nothing required, auto-merge merges a Dependabot PR at once, before any
# check has run. That rules out private repos (GitHub Free gives them no
# ruleset) and any repo with none of the gate workflows.
if [ "$visibility" = public ] && [ -n "$gates" ]; then
	auto_merge=true
else
	auto_merge=false
fi
jq --argjson auto_merge "$auto_merge" '. + {allow_auto_merge: $auto_merge}' \
	"$settings/repository.json" >"$repository_settings"

# Classic branch protection on the default branch, left in $protection.
# GitHub enforces it alongside the ruleset, not instead of it, so one that
# still requires checks the workflows no longer report blocks every merge
# however the ruleset reads. A 404 means the branch has none, and private
# repos on GitHub Free cannot have it at all; anything else aborts. Called
# directly, never in $(...), so that the exit stops the script.
default_branch=$(gh api "repos/$repo" --jq .default_branch)
# A branch name may hold `#`, `?`, `;` or `$`, so it goes into a path encoded:
# unencoded, `release#1` would end the path at the `#` and its 404 would read
# as no protection. `/` stays as is, which is how the branches API takes it.
protection_endpoint=repos/$repo/branches/$(jq -rn --arg b "$default_branch" '$b | @uri | gsub("%2F"; "/")')/protection
has_classic_protection() {
	if gh api "$protection_endpoint" >"$protection" 2>"$api_error"; then
		return 0
	fi
	if grep -e 'HTTP 404' -e 'Upgrade to GitHub Pro' "$api_error" >/dev/null; then
		return 1
	fi
	echo "could not read $repo's branch protection:" >&2
	cat "$api_error" >&2
	exit 1
}
protection_summary() {
	jq -r '(.required_status_checks.contexts // [])
		| if length == 0 then "no status checks" else "requires " + join(", ") end' "$protection"
}

if [ "$mode" = --diff ]; then
	# Command substitution drops trailing newlines, so print each part rather
	# than concatenating them.
	repository=$(drift "repos/$repo" "$repository_settings")
	workflow=$(drift "repos/$repo/actions/permissions/workflow" "$workflow_settings")
	classic=
	if has_classic_protection; then
		classic="  classic branch protection on $default_branch ($(protection_summary)) -> none, the ruleset replaces it"
	fi
	if [ -n "$repository$workflow$classic" ]; then
		echo "$repo differs from settings/ (live -> tracked):"
		[ -z "$repository" ] || echo "$repository"
		[ -z "$workflow" ] || echo "$workflow"
		[ -z "$classic" ] || echo "$classic"
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

echo "$repo is $visibility"

# Auto-merge is switched on only after the ruleset that gates it is in place
# (below), so a failure in between never leaves it on with nothing required.
if [ "$auto_merge" = true ]; then
	run gh api -X PATCH "repos/$repo" --silent --input "$settings/repository.json"
else
	run gh api -X PATCH "repos/$repo" --silent --input "$repository_settings"
fi
echo "auto-merge: $auto_merge (Dependabot's patch and minor bumps merge themselves only if so)"
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

	# The Copilot review rule only where the Copilot auto-merge pilot runs
	# (scripts/ruleset.jq).
	copilot_review=false
	case "
$workflows
" in
	*"
.github/workflows/copilot-auto-merge.yml
"*) copilot_review=true ;;
	esac
	ruleset=$(jq -c --arg gates "$gates" --arg admin_bypass "$admin_bypass" \
		--arg copilot_review "$copilot_review" \
		-f "$here/scripts/ruleset.jq" "$settings/ruleset-main.json")
	if [ -n "$gates" ]; then
		echo "requires: $(printf '%s' "$gates" | paste -sd, - | sed 's/,/, /g')"
	else
		echo "requires no status checks: no workflow reports a gate"
	fi
	for file in $gateless; do
		echo "not required: no job in $file reports \"${file%.yml} gate\""
	done
	if [ "$admin_bypass" = true ]; then
		echo "admins may bypass the ruleset: the repo commits .github/admin-bypass"
	fi
	if [ "$copilot_review" = true ]; then
		echo "requests a Copilot review on every push: the repo has copilot-auto-merge.yml"
	fi
	existing=$(gh api "repos/$repo/rulesets" --jq '.[] | select(.name == "main") | .id')
	if [ -n "$existing" ]; then
		run gh api -X PUT "repos/$repo/rulesets/$existing" --silent --input - <<<"$ruleset"
	else
		run gh api -X POST "repos/$repo/rulesets" --silent --input - <<<"$ruleset"
	fi
	if [ "$auto_merge" = true ]; then
		run gh api -X PATCH "repos/$repo" --silent -F allow_auto_merge=true
	fi
	case "$gates" in
	*"pull-request gate"*"checks gate"*"ci gate"*) ;;
	*)
		# The gates come from the workflows on the default branch, so a PR
		# that adds one is not required until it merges.
		echo "only gates whose workflow is on $default_branch are required: if a" \
			"PR adds one, rerun --apply after it merges"
		;;
	esac
	# Left in place rather than deleted: it can hold settings the ruleset does
	# not, and removing it is the owner's call.
	if has_classic_protection; then
		echo "warning: $default_branch also has classic branch protection" \
			"($(protection_summary)). GitHub enforces both, so a check it requires" \
			"that no workflow reports blocks every merge. Once the ruleset covers" \
			"it, remove it with:" >&2
		# Quoted with %q, so the line is safe to paste whatever the name holds.
		printf '  gh api -X DELETE %q\n' "$protection_endpoint" >&2
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
