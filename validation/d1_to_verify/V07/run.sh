#!/usr/bin/env bash
# Plan the configuration offline and list, per aws_db_instance, the planned value of the attributes of interest.
# Usage: bash run.sh. Writes output.log, plan.json, output/facts.txt.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
. ../common.sh
mkdir -p output
probe_case . > output/summary.txt
py -3.12 -I ../plan_facts.py plan.json --type aws_db_instance > output/facts.txt
cat output/summary.txt output/facts.txt
