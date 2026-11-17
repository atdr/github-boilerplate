# Prints, one per line, the check name each job in the workflow on stdin
# reports under its own `name:`. A job's name is the `name:` key directly under
# its job id in the top level `jobs:` mapping, so the workflow's own `name:` and
# a step's `- name:` never count. Plain, single quoted and double quoted values
# are read, keys may be quoted or spaced before the colon, a trailing comment
# is dropped, and CRLF endings are accepted.
#
# A job that calls a reusable workflow (`uses:` at job level) prints nothing:
# its checks are named `<name> / <called job>`, never `<name>` alone.
#
# A job this line based reading cannot be sure of prints `?<job>: <reason>`
# instead: a name over several lines, a block scalar, an expression, a double
# quoted escape, a flow mapping, an anchor, alias or merge key. configure.sh stops on that rather than guess, since a
# wrong guess either requires a check that never reports (every merge blocked)
# or drops one that does (auto-merge merging without it).
#
# Not a YAML parser, so configure.sh needs nothing beyond awk. POSIX awk only:
# macOS ships BWK awk, which has no gensub.

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

# The key `k`, bare or quoted, then optional space and the colon.
function key(k) {
	return "^[ \t]*(" k "|\"" k "\"|'" k "')[ \t]*:"
}

function start_job(line) {
	in_job = 1
	name = ""
	bad = ""
	uses = 0
	after_name = 0
	job_id = line
	sub(/^[ \t]+/, "", job_id)
	rest = job_id
	sub(/[ \t]*:.*/, "", job_id)
	sub(/^[^:]*:[ \t]*/, "", rest)
	# A job id with its value on the same line: a flow mapping or an alias.
	if (rest != "")
		bad = "not a block mapping"
}

function flush() {
	if (!in_job)
		return
	# A reusable call reports no check of its own name, readable or not.
	if (uses)
		;
	else if (bad != "")
		print "?" job_id ": " bad
	else if (name != "")
		print name
	in_job = 0
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
	flush()
	in_jobs = 0
	if (match(line, key("jobs"))) {
		if (substr(line, RLENGTH + 1) ~ /^[ \t]*$/)
			in_jobs = 1
		else
			print "?jobs: not a block mapping"
	}
	job_indent = -1
	prop_indent = -1
	next
}

!in_jobs { next }

# The first line under `jobs:` fixes the indent of the job ids.
job_indent < 0 { job_indent = depth }

depth < job_indent { next }

depth == job_indent {
	flush()
	start_job(line)
	prop_indent = -1
	next
}

# The first line under a job id fixes the indent of its properties.
prop_indent < 0 { prop_indent = depth }

# A name is a scalar, so a deeper line straight after it continues it.
depth > prop_indent {
	if (after_name)
		bad = "name: spans several lines"
	after_name = 0
	next
}

depth == prop_indent {
	after_name = 0
	if (match(line, key("name"))) {
		raw = substr(line, RLENGTH + 1)
		sub(/^[ \t]+/, "", raw)
		value = unquote(raw)
		if (value == "" || value ~ /^[|>&*!]/)
			bad = "name: is not a one line value"
		# GitHub evaluates the expression, so the check name is not this text.
		else if (value ~ /\$\{\{/)
			bad = "name: uses an expression"
		# YAML decodes the escape, so the check name is not this text either.
		else if (raw ~ /^"/ && value ~ /\\/)
			bad = "name: has an escape"
		else {
			# A single quoted '' is one quote.
			if (raw ~ /^'/)
				gsub(/''/, "'", value)
			name = value
			after_name = 1
		}
	} else if (match(line, key("uses")))
		uses = 1
	else if (line ~ /^[ \t]*<<[ \t]*:/)
		bad = "merge key"
}

END { flush() }
