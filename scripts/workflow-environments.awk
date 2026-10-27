# Prints the name of every deployment environment the workflows on stdin
# name, one per line, in each form a job can declare it:
#
#   environment: pypi                  (plain, single or double quoted)
#   environment: { name: pypi, url: x }
#   environment:
#     name: pypi
#
# A line-based reading, not a YAML parser, so configure.sh needs nothing beyond
# awk. POSIX awk only: macOS ships BWK awk, which has no gensub.

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
	sub(/[ \t]+#.*/, "", line)
	sub(/^[ \t]*#.*/, "", line)
	if (line ~ /^[ \t]*$/)
		next
}

# Inside a block mapping under `environment:`: look for its name, and leave it
# at the first line indented no deeper than the key.
block {
	if (indent(line) <= block_indent) {
		block = 0
	} else {
		if (match(line, /^[ \t]*name:/))
			print unquote(substr(line, RLENGTH + 1))
		next
	}
}

match(line, /^[ \t]*environment:/) {
	value = unquote(substr(line, RLENGTH + 1))
	key_indent = indent(line)
	if (value == "") {
		block = 1
		block_indent = key_indent
	} else if (value ~ /^\{/) {
		if (match(value, /name:[ \t]*[^,}]+/)) {
			name = substr(value, RSTART, RLENGTH)
			sub(/^name:/, "", name)
			print unquote(name)
		}
	} else {
		print value
	}
}
