#!/usr/bin/env bash
# V03: what does CKV_AWS_17 check? One minimal configuration per variant, Checkov 3.3.30 from .venv-tools.
# Usage: bash run.sh (needs .venv-tools with the pinned lock file installed).
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
ROOT="$(cd ../../.. && pwd)"
export PATH="$ROOT/.venv-tools/Scripts:$ROOT/.venv-tools/bin:$PATH"
export CHECKPOINT_DISABLE=1
mkdir -p output
{ echo "$ checkov --version"; checkov --version; } > output/checkov_version.txt 2>&1
for d in */; do
  d="${d%/}"
  [ "$d" = output ] && continue
  checkov -d "$d" --framework terraform --compact --output json --check CKV_AWS_17 --skip-download > "$d/checkov.json" 2>/dev/null
done
py -3.12 -I ../checkov_summary.py CKV_AWS_17 $(ls -d */ | tr -d / | grep -v '^output$') > output/summary.txt
cat output/summary.txt
