#!/usr/bin/env bash
set -euo pipefail

# Generate a changelog from git history between tags.
# Usage: generate-changelog.sh <current-tag>
#
# Generates changelog between the previous tag and current-tag.
# If no previous tag exists, includes all commits up to current-tag.
#
# Output: Markdown-formatted changelog to stdout.

CURRENT_TAG="${1:?Usage: generate-changelog.sh <current-tag>}"

# Find the previous tag
PREV_TAG=$(git describe --tags --abbrev=0 "${CURRENT_TAG}^" 2>/dev/null || true)

if [[ -z "$PREV_TAG" ]]; then
	RANGE="$CURRENT_TAG"
else
	RANGE="${PREV_TAG}..${CURRENT_TAG}"
fi

# Collect commits
mapfile -t COMMITS < <(
	git log "$RANGE" --oneline
)

if [[ ${#COMMITS[@]} -eq 0 ]]; then
	echo "## What's New"
	echo ""
	echo "Initial release."
	exit 0
fi

# Categorise commits by conventional commit type
declare -A CATEGORIES=(
	[feat]="Features"
	[fix]="Bug Fixes"
	[refactor]="Refactoring"
	[perf]="Performance"
	[docs]="Documentation"
	[test]="Tests"
	[style]="Style"
	[chore]="Chores"
)
CATEGORY_ORDER=(feat fix refactor perf docs test style chore)

declare -A CATEGORISED
UNCATEGORISED=()

for commit in "${COMMITS[@]}"; do
	hash="${commit%% *}"
	message="${commit#* }"

	# Match conventional commit prefix: type(scope): or type:
	cc_pattern='^([a-z]+)(\([^)]*\))?: (.+)$'
	if [[ "$message" =~ $cc_pattern ]]; then
		type="${BASH_REMATCH[1]}"
		description="${BASH_REMATCH[3]}"
		if [[ -n "${CATEGORIES[$type]:-}" ]]; then
			CATEGORISED[$type]+="- ${description} (\`${hash}\`)"$'\n'
		else
			UNCATEGORISED+=("- ${message} (\`${hash}\`)")
		fi
	else
		UNCATEGORISED+=("- ${message} (\`${hash}\`)")
	fi
done

# Output
echo "## What's Changed"
echo ""

for type in "${CATEGORY_ORDER[@]}"; do
	if [[ -n "${CATEGORISED[$type]:-}" ]]; then
		echo "### ${CATEGORIES[$type]}"
		echo ""
		echo -n "${CATEGORISED[$type]}"
		echo ""
	fi
done

if [[ ${#UNCATEGORISED[@]} -gt 0 ]]; then
	echo "### Other"
	echo ""
	for item in "${UNCATEGORISED[@]}"; do
		echo "$item"
	done
	echo ""
fi
