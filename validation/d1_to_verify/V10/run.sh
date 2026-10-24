#!/usr/bin/env bash
# V10: implicit moves for count / for_each in Terraform 1.15, with the built-in terraform_data resource.
# terraform_data needs no provider and no network. This is the ONLY probe that runs `terraform apply`,
# and only against local state in a throw-away directory (work/, ignored by git).
# Usage: bash run.sh. Writes output/<case>.txt (plan text after the config change), output/summary.txt.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
. ../common.sh
export HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9
mkdir -p output work
: > output/summary.txt

# case <name> <from-config> <to-config>
case_run() {
  local name="$1" from="$2" to="$3" log="output/$1.txt"
  : > "$log"
  rm -rf work && mkdir work
  cp "configs/$from.tf" work/main.tf
  ( cd work || exit 1
    terraform init -input=false > /dev/null 2>&1
    terraform apply -input=false -auto-approve -no-color > /dev/null 2>&1 )
  printf 'applied configs/%s.tf; state before the change:\n' "$from" >> "$log"
  ( cd work && terraform state list -no-color ) >> "$log" 2>&1
  cp "configs/$to.tf" work/main.tf
  printf '\nchanged to configs/%s.tf; `terraform plan -no-color`:\n$ terraform plan -input=false -no-color\n' "$to" >> "$log"
  ( cd work && terraform plan -input=false -no-color ) 2>&1 | sed "s/${ANSI_ESCAPE}//g" >> "$log"
  # machine-readable: actions and previous_address per resource_changes entry
  ( cd work && terraform plan -input=false -out=p.bin > /dev/null 2>&1 && terraform show -json p.bin ) > work/p.json 2>/dev/null
  py -3.12 -I - work/p.json "$name" >> output/summary.txt <<'PY'
import json, sys
plan = json.load(open(sys.argv[1], encoding="utf-8"))
rows = [
    f"{c['address']}: actions={c['change']['actions']}"
    + (f" previous_address={c['previous_address']}" if c.get("previous_address") else "")
    for c in plan.get("resource_changes", [])
]
print(f"{sys.argv[2]:36s} " + ("; ".join(rows) if rows else "no changes"))
PY
}

case_run C1_none_to_count1             single     count1
case_run C2_count1_to_none             count1     single
case_run C3_none_to_foreach_a          single     foreach_a
case_run C4_count1_to_foreach_a        count1     foreach_a
case_run C5_foreach_a_to_none          foreach_a  single
case_run C6_foreach_a_to_count1        foreach_a  count1
case_run C7_none_to_count2             single     count2
case_run C8_count2_to_none             count2     single
case_run M3_none_to_foreach_a_moved    single     single_moved_to_foreach_a
case_run M4_count1_to_foreach_a_moved  count1     count1_moved_to_foreach_a
case_run M6_foreach_a_to_count1_moved  foreach_a  foreach_a_moved_to_count1
rm -rf work
