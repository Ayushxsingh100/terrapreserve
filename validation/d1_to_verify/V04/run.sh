#!/usr/bin/env bash
# V04: what does CKV_AWS_24 really check? One minimal configuration per variant, Checkov 3.3.30 from .venv-tools.
# Usage (from the repository root, after `py -3.12 -m venv .venv-tools` and
# `.venv-tools/Scripts/python -m pip install -r requirements-tools.lock.txt`):  bash validation/d1_to_verify/V04/run.sh
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
  checkov -d "$d" --framework terraform --compact --output json --check CKV_AWS_24 --skip-download > "$d/checkov.json" 2>/dev/null
  echo "$d exit=$?" >> output/exit_codes.txt
done
py -3.12 -I ../checkov_summary.py CKV_AWS_24 $(ls -d */ | tr -d / | grep -v '^output$') > output/summary.txt
cat output/summary.txt
