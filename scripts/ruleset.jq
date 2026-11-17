# The main ruleset for one repo: settings/ruleset-main.json with its required
# status checks cut down to the gates the repo's workflows report.
#
# $gates is a newline separated list of the gates present (`ci gate`, ...).
# The core gates come from the file; ci gate is added where present. With no
# gate present the required_status_checks rule is dropped, since a rule
# requiring nothing is rejected and one requiring an absent check blocks
# every merge.
#
# $admin_bypass is "true" where the repo commits .github/admin-bypass: the
# repository admin role may then push to the default branch directly, while
# everyone else (Dependabot included) still goes through a gated PR.
#
# $copilot_review is "true" where the repo has copilot-auto-merge.yml. The
# Copilot review rule is kept only there: that workflow is what needs a fresh
# review on every push, and elsewhere the rule would spend Copilot credits on
# reviews nothing acts on.

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
| .rules |= map(select(.type != "copilot_code_review" or $copilot_review == "true"))
| .bypass_actors = (if $admin_bypass == "true"
    then [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]
    else [] end)
