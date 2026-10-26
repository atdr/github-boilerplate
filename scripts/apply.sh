#!/usr/bin/env bash
# Copies the boilerplate into a repository: template/core first, then the
# overlay for its ecosystem, which wins where both have a file.
#
# Usage: scripts/apply.sh <node|python|tex|core> <target-dir> [--force]
#
# Existing files in the target are left alone and listed, unless --force.
# Placeholders (__OWNER__, __REPO__) are filled from the target's origin
# remote, and reusable workflow pins are set to this boilerplate's current
# release. Written for bash 3.2 (macOS's stock /bin/bash).

set -euo pipefail

usage() {
	echo "usage: $0 <node|python|tex|core> <target-dir> [--force]" >&2
	exit 2
}

[ $# -ge 2 ] || usage
overlay=$1
target=$2
force=${3:-}
[ -z "$force" ] || [ "$force" = --force ] || usage

here=$(cd "$(dirname "$0")/.." && pwd)
case "$overlay" in
core) sources=("$here/template/core") ;;
node | python | tex) sources=("$here/template/core" "$here/template/$overlay") ;;
*) usage ;;
esac
[ -d "$target" ] || {
	echo "$target is not a directory" >&2
	exit 1
}
target=$(cd "$target" && pwd)

# owner/repo from a GitHub origin remote, falling back to the directory name.
remote=$(git -C "$target" remote get-url origin 2>/dev/null || true)
slug=
case "$remote" in
*github.com[:/]*/*) slug=$(printf '%s' "$remote" | sed -E 's#^.*github\.com[:/]##; s#\.git$##') ;;
esac
if [ -n "$slug" ]; then
	owner=${slug%%/*}
	repo=${slug#*/}
else
	owner=atdr
	repo=$(basename "$target")
	echo "No GitHub origin remote; assuming $owner/$repo" >&2
fi

version=$(jq -r '."."' "$here/.release-please-manifest.json")
if [ "$version" = 0.0.0 ]; then
	ref=main
	echo "github-boilerplate has no release yet; pinning its workflows to @main" >&2
else
	ref=v$version
fi

copied=()
skipped=()
# Overlay files replace core files of the same path, so settle the winning
# source for each path (the last one listed) before copying anything.
winners=$(
	for src in "${sources[@]}"; do
		(cd "$src" && find . \( -type f -o -type l \) | sed 's#^\./##') |
			while IFS= read -r rel; do printf '%s\t%s\n' "$rel" "$src"; done
	done | awk -F '\t' '{ w[$1] = $2 } END { for (p in w) print p "\t" w[p] }' | sort
)

while IFS="$(printf '\t')" read -r rel src; do
	dest="$target/$rel"
	if { [ -e "$dest" ] || [ -L "$dest" ]; } && [ "$force" != --force ]; then
		skipped+=("$rel")
		continue
	fi
	mkdir -p "$(dirname "$dest")"
	if [ -L "$src/$rel" ]; then
		rm -f "$dest"
		ln -s "$(readlink "$src/$rel")" "$dest"
	else
		sed -e "s#__OWNER__#$owner#g" \
			-e "s#__REPO__#$repo#g" \
			-e "s#@v[0-9][0-9.]* \# x-release-please-version#@$ref#g" \
			-e "s#Copyright (c) [0-9]\{4\}#Copyright (c) $(date +%Y)#" \
			"$src/$rel" >"$dest"
		[ ! -x "$src/$rel" ] || chmod +x "$dest"
	fi
	copied+=("$rel")
done <<<"$winners"

# The core README's CI and coverage badges point at ci.yml, which only the
# language overlays ship. Drop them from a README this run wrote.
if [ ! -f "$target/.github/workflows/ci.yml" ]; then
	for rel in "${copied[@]}"; do
		if [ "$rel" = README.md ]; then
			sed -e '/^\[!\[CI\]/d' -e '/^\[!\[Coverage\]/d' "$target/README.md" >"$target/README.md.tmp"
			mv "$target/README.md.tmp" "$target/README.md"
		fi
	done
fi

echo "Applied $overlay to $owner/$repo at $target"
echo "  copied: ${#copied[@]} file(s)"
if [ ${#skipped[@]} -gt 0 ]; then
	echo "  skipped, already present (compare by hand, or rerun with --force):"
	printf '    %s\n' "${skipped[@]}"
fi

echo
echo "Next:"
case "$overlay" in
node)
	echo "  npm install --save-dev husky @commitlint/cli @commitlint/config-conventional prettier"
	echo "  npm pkg set scripts.prepare=husky"
	echo "  define the npm scripts ci.yml runs (lint, format:check, test) and coverage (writes lcov.info)"
	;;
python | tex)
	echo "  pre-commit install"
	;;
esac
echo "  fill in the README and AGENTS.md skeletons"
echo "  scripts/configure.sh $owner/$repo   (repo settings, ruleset, environments)"
