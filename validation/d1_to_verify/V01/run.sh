#!/usr/bin/env bash
# V01: offline `terraform plan` for the nine types plus aws_db_subnet_group, with mock credentials.
# Usage: bash run.sh   (from anywhere). Writes output/*.txt and plan.json. Needs terraform 1.15.x, python 3.12.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
. ../common.sh
mkdir -p output
LOG=output/commands.log
: > "$LOG"

run "$LOG" terraform version
run "$LOG" terraform init -input=false -lockfile=readonly
run "$LOG" terraform fmt -check -recursive
run "$LOG" terraform validate

# Network blocked: any HTTP(S) request from Terraform or the provider must go to an unreachable proxy.
export HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9
unset NO_PROXY no_proxy
run "$LOG" terraform plan -input=false -out=plan.bin
terraform show -json plan.bin > plan.json 2>> "$LOG"
printf '$ terraform show -json plan.bin > plan.json\n[exit %s]\n\n' "$?" >> "$LOG"
terraform show -no-color plan.bin > output/plan_text.txt 2>&1
rm -f plan.bin

# What did the provider try to contact? (DEBUG log of a second plan; counts only the relevant lines)
rm -f output/debug.log
TF_LOG=DEBUG TF_LOG_PATH=output/debug.log terraform plan -input=false > /dev/null 2>&1
{
  echo "debug.log lines:                      $(wc -l < output/debug.log)"
  echo "lines mentioning amazonaws.com:       $(grep -c 'amazonaws\.com' output/debug.log)"
  echo "lines mentioning proxyconnect:        $(grep -c 'proxyconnect' output/debug.log)"
  echo "lines mentioning 'Sending' requests:  $(grep -ci 'sending request\|http request' output/debug.log)"
  echo "lines mentioning skip/credentials:    $(grep -ci 'skip\|credential' output/debug.log)"
} > output/network_evidence.txt
rm -f output/debug.log

python3 -I ../plan_facts.py plan.json > output/plan_facts.txt 2>&1 || py -3.12 -I ../plan_facts.py plan.json > output/plan_facts.txt 2>&1

# Control: same unreachable proxy, skip flags removed -> the plan must FAIL with a proxy connection error.
(
  cd control_network_on
  run ../output/control_commands.log terraform init -input=false -lockfile=readonly
  run ../output/control_commands.log terraform plan -input=false
)
