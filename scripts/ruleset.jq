# The main ruleset for one repo: settings/ruleset-main.json with its required
# status checks cut down to the gates the repo's workflows report.
#
# $gates is a newline separated list of the gates present (`ci gate`, ...).
# The core gates come from the file; ci gate is added where present. With no
# gate present the required_status_checks rule is dropped, since a rule
# requiring nothing is rejected and one requiring an absent check blocks
# every merge.

($gates | split("\n") | map(select(. != ""))) as $present
| .rules |= map(
    if .type == "required_status_checks" then
      .parameters.required_status_checks |=
        (map(select(.context as $c | $present | index($c)))
          + (if $present | index("ci gate")
             then [{"context": "ci gate", "integration_id": 15368}]
             else [] end))
    else . end)
| .rules |= map(select(.type != "required_status_checks"
    or (.parameters.required_status_checks | length) > 0))
