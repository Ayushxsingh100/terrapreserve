# shellcheck shell=bash
# Sourced by every probe's run.sh. Offline, mock-credential environment for the D1 TO-VERIFY probes.
#
# Credentials are mock values, supplied through the environment only; no .tf file contains any.
# No probe runs `terraform apply` against AWS (V10 applies only the built-in terraform_data resource,
# with local state, and needs no provider and no credentials).
export AWS_ACCESS_KEY_ID=mock
export AWS_SECRET_ACCESS_KEY=mock
export AWS_REGION=us-east-1
export AWS_EC2_METADATA_DISABLED=true
export CHECKPOINT_DISABLE=1   # no version-check call home
export TF_IN_AUTOMATION=1
export TF_INPUT=0

# Optional, machine-local: install the pinned provider from a local filesystem mirror seeded with the
# identical 6.53.0 binary (the lock-file hashes still apply), and share one initialised data dir across probes.
# Without these set, `terraform init` downloads the provider from the registry as usual.
#   TF_CLI_CONFIG_FILE  a CLI config with a filesystem_mirror for hashicorp/aws
#   TF_DATA_DIR         one shared .terraform directory (the provider binary is ~880 MB)

PROBE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSI_ESCAPE=$'\033\\[[0-9;]*m'

# run <logfile> <command...>  appends "$ command", the output (colour codes removed) and "[exit N]" to the log.
run() {
  local log="$1"; shift
  { printf '$ %s\n' "$*"; } >> "$log"
  "$@" 2>&1 | sed "s/${ANSI_ESCAPE}//g" >> "$log"
  local rc=${PIPESTATUS[0]}
  printf '[exit %s]\n\n' "$rc" >> "$log"
  return "$rc"
}

# probe_case <dir>  init + validate + plan in <dir> (offline: unreachable proxy), writing <dir>/output.log
# and, when the plan succeeds, <dir>/plan.json. Prints one summary line: "<dir> validate=<rc> plan=<rc>".
probe_case() {
  local dir="$1" vrc=0 prc=0
  (
    cd "$dir" || exit 99
    : > output.log
    export HTTPS_PROXY=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9
    unset NO_PROXY no_proxy
    run output.log terraform init -input=false -lockfile=readonly || exit 98
    run output.log terraform validate; vrc=$?
    run output.log terraform plan -input=false -out=plan.bin; prc=$?
    if [ "$prc" -eq 0 ]; then
      terraform show -json plan.bin > plan.json 2>/dev/null
    else
      rm -f plan.json
    fi
    rm -f plan.bin
    echo "validate=$vrc plan=$prc" > .rc
  )
  echo "$dir $(cat "$dir/.rc") "
  rm -f "$dir/.rc"
}
