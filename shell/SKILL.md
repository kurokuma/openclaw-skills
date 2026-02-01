---
name: shell
description: Execute shell commands (Bash). By default uses an allowlist and blocks dangerous commands; use --unsafe to bypass (at your own risk).
---

# Shell Command Runner Skill

This skill executes a shell command provided as a single argument string.

## Usage

- Safe mode (default): blocks dangerous commands and only allows a conservative set of tools.
  - `bash run.sh "ls -la"`
  - `bash run.sh "cat /etc/os-release"`
  - `bash run.sh "curl -I https://example.com"`

- Unsafe mode (bypass filters):
  - `bash run.sh --unsafe "rm -rf /tmp/testdir"`  (DANGEROUS)

## Output

- Prints stdout/stderr from the executed command.
- Exits with the command exit code.

## Notes / Safety

Safe mode blocks commands that appear to:
- modify system state broadly (rm/mkfs/dd, etc.)
- change permissions/ownership
- install packages
- access sensitive locations
- use shell metacharacters for chaining/piping/redirection

Use `--unsafe` only in tightly controlled environments.

## Scripts

- `run.sh`: Executes the command with guardrails (safe mode) or without (unsafe mode).
