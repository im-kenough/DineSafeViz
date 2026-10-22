#!/usr/bin/env bash
# Prints each change in a saved Terraform plan and a one-line count, and
# fails if the plan deletes or replaces anything. `make plan` runs it on
# every plan, so a destroy never reaches `make apply` by accident.
#
# Usage: plan-summary.sh <plan.json>     (from `terraform show -json`)
# Set ALLOW_DESTROY=1 to allow deletes and replaces (for `make destroy`).
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <plan.json>" >&2
    exit 2
fi
if [[ ! -f $1 ]]; then
    echo "ERROR: $1 not found" >&2
    exit 2
fi

# One line per managed resource that isn't a plain no-op:
# "<kind>  <address>", where kind is create, update, delete, replace,
# import, or import+<action>.
jq -r '
  .resource_changes[]? | select(.mode == "managed")
  | (.change.actions) as $a
  | (if ($a | index("delete")) and ($a | index("create")) then "replace"
     elif $a == ["create"] then "create"
     elif $a == ["update"] then "update"
     elif $a == ["delete"] then "delete"
     else "no-op" end) as $kind
  | (if .change.importing then (if $kind == "no-op" then "import" else "import+" + $kind end) else $kind end) as $label
  | select($label != "no-op")
  | "\($label)  \(.address)"
' "$1"

read -r imports adds changes replaces destroys < <(jq -r '
  [.resource_changes[]? | select(.mode == "managed")] as $rc
  | def n(f): [$rc[] | select(f)] | length;
  [ n(.change.importing != null),
    n(.change.actions == ["create"]),
    n(.change.actions == ["update"]),
    n((.change.actions | index("delete")) and (.change.actions | index("create"))),
    n(.change.actions == ["delete"]) ] | @tsv
' "$1")

echo "Plan: $imports to import, $adds to add, $changes to change, $replaces to replace, $destroys to destroy."

if (( replaces + destroys > 0 )) && [[ ${ALLOW_DESTROY:-0} != 1 ]]; then
    echo "ERROR: refusing a plan that deletes or replaces resources." >&2
    echo "Change the code, or use the destroy target where one exists." >&2
    exit 1
fi
