#!/usr/bin/env bash
# V09: are upper-case protocols accepted, and what does the plan JSON show for each spelling and rule form?
# Usage: bash run.sh. Writes output.log, plan.json and output/protocols.txt.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
. ../common.sh
mkdir -p output
probe_case . > output/summary.txt
py -3.12 -I - <<'PY' > output/protocols.txt
import json, re
plan = json.load(open("plan.json", encoding="utf-8"))
src = open("main.tf", encoding="utf-8").read()
# configured value per resource name, read from the .tf text
configured = {}
for name, body in re.findall(r'resource "aws_security_group(?:_rule)?" "(p\d\d)" \{(.*?)\n\}', src, re.S):
    configured[name] = re.search(r'protocol\s*=\s*"([^"]*)"', body).group(1)
print(f"{'configured':>10}  {'rule form: plan protocol':26} {'inline form: plan ingress protocol'}")
rows = {}
for rc in plan["resource_changes"]:
    if rc["name"] not in configured:
        continue
    after = rc["change"]["after"]
    if rc["type"] == "aws_security_group_rule":
        rows.setdefault(rc["name"], {})["rule"] = after["protocol"]
    elif rc["type"] == "aws_security_group":
        ing = after.get("ingress")
        rows.setdefault(rc["name"], {})["inline"] = [i["protocol"] for i in ing] if isinstance(ing, list) else ing
for name in sorted(rows):
    print(f"{configured[name]!r:>10}  {rows[name].get('rule')!r:26} {rows[name].get('inline')!r}")
PY
