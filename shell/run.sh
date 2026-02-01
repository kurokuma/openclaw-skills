#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  bash run.sh "COMMAND"
  bash run.sh --unsafe "COMMAND"

Modes:
  default (safe): allowlist-based, blocks dangerous patterns.
  --unsafe: executes as-is (no filters). EXTREMELY DANGEROUS.

Examples:
  bash run.sh "ls -la"
  bash run.sh "uname -a"
  bash run.sh --unsafe "echo hi > /tmp/x"

EOF
}

UNSAFE="0"
CMD=""

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

if [[ "${1:-}" == "--unsafe" ]]; then
  UNSAFE="1"
  shift
fi

if [[ $# -ne 1 ]]; then
  echo "error: provide the command as a single quoted string" >&2
  usage
  exit 2
fi

CMD="$1"

if [[ -z "${CMD}" ]]; then
  echo "error: empty command" >&2
  exit 2
fi

# -----------------------------
# Safe-mode guardrails
# -----------------------------
# Strategy:
# 1) Block obvious dangerous commands
# 2) Block shell metacharacters that enable chaining/redirection/piping
# 3) Allow only a conservative first-word allowlist
#
# You can tune ALLOW_CMDS / BLOCK_PATTERNS as needed.

ALLOW_CMDS=(
  ls cat head tail wc sort uniq cut tr sed awk grep find
  pwd whoami id uname date env printenv
  curl wget
  ping dig nslookup host
  ip ss netstat
  df du free
  ps top
  tar gzip gunzip zip unzip
  python python3 node npm
)

# block metacharacters in safe mode to avoid arbitrary chaining
BLOCK_META_REGEX='[;&|`$()<>\\]'

# block high-risk commands/keywords
BLOCK_WORD_REGEX='(^|[[:space:]])(sudo|su|rm|mv|cp|chmod|chown|mkfs|dd|mount|umount|apt|apt-get|dnf|yum|pacman|snap|systemctl|service|crontab|useradd|usermod|groupadd|passwd|ssh|scp|sftp|rsync|docker|podman|kubectl|terraform)([[:space:]]|$)'

# block sensitive paths in safe mode
BLOCK_PATH_REGEX='(^|[[:space:]])(/etc/|/var/lib/|/root/|~/?\.ssh/)([^[:space:]]*)'

first_word() {
  # extract first token (naive but ok for guardrails)
  awk '{print $1}' <<<"$1"
}

is_allowed_cmd() {
  local w="$1"
  for a in "${ALLOW_CMDS[@]}"; do
    if [[ "$w" == "$a" ]]; then
      return 0
    fi
  done
  return 1
}

if [[ "${UNSAFE}" == "0" ]]; then
  # metacharacters
  if [[ "${CMD}" =~ ${BLOCK_META_REGEX} ]]; then
    echo "blocked: command contains shell metacharacters (safe mode)" >&2
    exit 3
  fi

  # dangerous words
  if [[ "${CMD}" =~ ${BLOCK_WORD_REGEX} ]]; then
    echo "blocked: command contains high-risk keywords (safe mode)" >&2
    exit 3
  fi

  # sensitive paths
  if [[ "${CMD}" =~ ${BLOCK_PATH_REGEX} ]]; then
    echo "blocked: command references sensitive paths (safe mode)" >&2
    exit 3
  fi

  # allowlist check on first word
  w="$(first_word "${CMD}")"
  if ! is_allowed_cmd "${w}"; then
    echo "blocked: '${w}' is not in allowlist (safe mode)" >&2
    echo "allowed: ${ALLOW_CMDS[*]}" >&2
    exit 3
  fi
fi

# -----------------------------
# Execute
# -----------------------------
# Use bash -lc to run in a login-like context, but in safe mode we disallow meta anyway.
# In unsafe mode, it is truly arbitrary.
set +e
bash -lc "${CMD}"
rc=$?
set -e
exit $rc
