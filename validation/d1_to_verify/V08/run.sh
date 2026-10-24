#!/usr/bin/env bash
# V08: are host-bit and malformed CIDRs rejected at validate/plan time? One tiny configuration per case.
# Usage: bash run.sh. Writes <case>/output.log, <case>/plan.json (successful plans only) and output/summary.txt.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
. ../common.sh
mkdir -p output
: > output/summary.txt
for dir in */; do
  dir="${dir%/}"
  [ "$dir" = output ] && continue
  probe_case "$dir" >> output/summary.txt
done
# First error summary line per failing case.
{
  echo
  for dir in */; do
    dir="${dir%/}"
    [ "$dir" = output ] && continue
    echo "== $dir"
    grep -m3 -E "^Error: |Error: " "$dir/output.log" | sed 's/^/   /'
  done
} >> output/summary.txt
