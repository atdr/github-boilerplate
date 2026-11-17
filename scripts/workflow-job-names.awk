# Prints the `name:` of every job in the workflow on stdin, one per line. A
# job's name is the `name:` key directly under its job id in the top level
# `jobs:` mapping, so the workflow's own `name:` and a step's `- name:` never
# count. Plain, single quoted and double quoted values are read, and a trailing
# comment is dropped.
#
# A line-based reading, not a YAML parser, so configure.sh needs nothing beyond
# awk. It does not read flow style (`name: x` inside `{ ... }`), anchors or
# block scalar names; a gate written that way reads as missing, which is the
# safe direction (the check is not required). POSIX awk only: macOS ships BWK
# awk, which has no gensub.

function unquote(value) {
	sub(/^[ \t]+/, "", value)
	sub(/[ \t]+$/, "", value)
	if (value ~ /^".*"$/ || value ~ /^'.*'$/)
		value = substr(value, 2, length(value) - 2)
	return value
}

function indent(line) {
	match(line, /^[ \t]*/)
	return RLENGTH
}

{
	line = $0
	# A workflow committed with CRLF endings decodes with a \r on every line.
	sub(/\r$/, "", line)
	sub(/[ \t]+#.*/, "", line)
	sub(/^[ \t]*#.*/, "", line)
	if (line ~ /^[ \t]*$/)
		next
	depth = indent(line)
}

# Any key at column 0 ends the jobs mapping; `jobs:` itself starts it.
depth == 0 {
	in_jobs = (line ~ /^jobs:[ \t]*$/)
	job_indent = -1
	prop_indent = -1
	next
}

!in_jobs { next }

# The first line under `jobs:` fixes the indent of the job ids.
job_indent < 0 { job_indent = depth }

depth == job_indent {
	prop_indent = -1
	next
}

# The first line under a job id fixes the indent of its properties.
prop_indent < 0 { prop_indent = depth }

depth == prop_indent && match(line, /^[ \t]*name:/) {
	print unquote(substr(line, RLENGTH + 1))
}
