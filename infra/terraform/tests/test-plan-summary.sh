#!/usr/bin/env bash
# Tests for plan-summary.sh, run by `make test`.
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script="$here/../plan-summary.sh"
fx="$here/fixtures"
fails=0

# check <name> <expected exit> <expected output substring> <command...>
check() {
    local name=$1 want_rc=$2 want_out=$3 out rc
    shift 3
    out=$("$@" 2>&1); rc=$?
    if [[ $rc -ne $want_rc || $out != *"$want_out"* ]]; then
        echo "FAIL $name: exit $rc (want $want_rc), output:"
        echo "$out"
        fails=$((fails + 1))
    else
        echo "ok   $name"
    fi
}

check "creates only" 0 "Plan: 0 to import, 2 to add, 0 to change, 0 to replace, 0 to destroy." \
    "$script" "$fx/create.json"
check "lists each create" 0 "create  azurerm_resource_group.iac" \
    "$script" "$fx/create.json"
check "ignores data sources" 0 "2 to add" \
    "$script" "$fx/create.json"
check "imports with and without update" 0 "Plan: 2 to import, 0 to add, 1 to change, 0 to replace, 0 to destroy." \
    "$script" "$fx/import-update.json"
check "marks imports" 0 "import+update  azuread_group.operators" \
    "$script" "$fx/import-update.json"
check "refuses delete" 1 "refusing a plan that deletes or replaces" \
    "$script" "$fx/delete.json"
check "refuses both replace orders" 1 "0 to add, 0 to change, 2 to replace, 0 to destroy." \
    "$script" "$fx/replace.json"
check "ALLOW_DESTROY allows delete" 0 "1 to destroy." \
    env ALLOW_DESTROY=1 "$script" "$fx/delete.json"
check "usage error" 2 "Usage:" \
    "$script"
check "missing file" 2 "not found" \
    "$script" "$fx/nope.json"

if [[ $fails -ne 0 ]]; then
    echo "$fails failed."
    exit 1
fi
echo "All plan-summary tests passed."
