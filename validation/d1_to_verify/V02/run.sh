#!/usr/bin/env bash
# V02: is there any Checkov check for ingress from 0.0.0.0/0 to TCP/5432? (Checkov 3.3.30 from .venv-tools)
# Usage from anywhere: bash run.sh. Writes output/*.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
ROOT="$(cd ../../.. && pwd)"
export PATH="$ROOT/.venv-tools/Scripts:$ROOT/.venv-tools/bin:$PATH"
export CHECKPOINT_DISABLE=1
mkdir -p output
{ echo "$ checkov --version"; checkov --version; } > output/checkov_version.txt 2>&1

# 1. every candidate check in the pinned version's catalogue
py -3.12 -I list_candidate_checks.py > output/candidate_checks.md

# 2. any occurrence of 5432 in the installed Checkov package (source, YAML and JSON policies)
SITE="$("$ROOT/.venv-tools/Scripts/python" -I -c "import os, checkov; print(os.path.dirname(checkov.__file__))" 2>/dev/null || "$ROOT/.venv-tools/bin/python" -I -c "import os, checkov; print(os.path.dirname(checkov.__file__))")"
{
  echo "$ grep -rIn 5432 <checkov package> --include=*.py --include=*.yaml --include=*.yml --include=*.json"
  grep -rIn "5432" "$SITE" --include=*.py --include=*.yaml --include=*.yml --include=*.json
  echo "[grep exit $? ; 1 means no match]"
} > output/grep_5432.txt 2>&1

# 3. run ALL terraform checks on a public and a private 5432 rule; compare the failed check ids
for d in public_5432 private_5432; do
  checkov -d "$d" --framework terraform --compact --output json --skip-download > "$d/checkov.json" 2>/dev/null
done
py -3.12 -I - <<'PY' > output/public_vs_private.txt
import json
def failed(d):
    raw = json.load(open(f"{d}/checkov.json", encoding="utf-8"))
    raw = raw[0] if isinstance(raw, list) else raw
    res = {}
    for item in raw["results"]["failed_checks"]:
        res.setdefault(item["resource"], set()).add(item["check_id"])
    passed = {}
    for item in raw["results"]["passed_checks"]:
        passed.setdefault(item["resource"], set()).add(item["check_id"])
    return res, passed
pub, pubp = failed("public_5432")
pri, prip = failed("private_5432")
print("FAILED check ids per resource")
for res in sorted(set(pub) | set(pri)):
    print(f"  {res}")
    print(f"    public  (0.0.0.0/0)  : {sorted(pub.get(res, []))}")
    print(f"    private (10.0.0.0/16): {sorted(pri.get(res, []))}")
    print(f"    only in public       : {sorted(pub.get(res, set()) - pri.get(res, set()))}")
print()
print("PASSED in public but FAILED/absent in private, or vice versa (any difference at all):")
for res in sorted(set(pubp) | set(prip)):
    d = (pubp.get(res, set()) ^ prip.get(res, set()))
    if d:
        print(f"  {res}: {sorted(d)}")
allfail_pub = set().union(*pub.values()) if pub else set()
allfail_pri = set().union(*pri.values()) if pri else set()
print()
print(f"check ids failing on the public configuration but not the private one: {sorted(allfail_pub - allfail_pri)}")
PY
cat output/public_vs_private.txt
