#!/usr/bin/env bash
set -euo pipefail

# curl-fetch skill
# - URL required
# - Optional:
#   --method GET|POST|PUT|PATCH|DELETE
#   --data 'k=v&k2=v2' (uses --data-raw)
#   --json '{"k":1}'   (sets Content-Type: application/json and uses --data-raw)
#   --header 'Key: Val' (repeatable)
#   --head             (HEAD request)
#   --max-time N       (total seconds)
#   --connect-timeout N
#   --output FILE      (write body to file)
#   --show-headers      (print response headers to stderr)
#   --no-follow         (disable redirects; default follows)
#   --insecure          (skip TLS verify)
#   --silent            (less curl progress; errors still shown)
#
# Notes:
# - By default follows redirects (-L)
# - Prints body to stdout unless --output is given

usage() {
  cat >&2 <<'EOF'
Usage:
  bash fetch.sh <URL> [options]

Options:
  --method METHOD         HTTP method (default: GET)
  --data STRING           Request body (form or raw)
  --json JSON             JSON body (sets Content-Type: application/json)
  --header "K: V"         Add header (repeatable)
  --head                  Use HEAD request
  --max-time N            Max total time seconds (default: 20)
  --connect-timeout N     Connect timeout seconds (default: 5)
  --output FILE           Write response body to FILE (default: stdout)
  --show-headers          Print response headers to stderr
  --no-follow             Do not follow redirects (default: follow)
  --insecure              Skip TLS verification
  --silent                Less output (keeps errors)
  -h, --help              Show help

Examples:
  bash fetch.sh https://example.com
  bash fetch.sh https://httpbin.org/post --method POST --data 'a=1&b=2'
  bash fetch.sh https://httpbin.org/post --method POST --json '{"a":1}'
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

URL=""
METHOD="GET"
DATA=""
JSON_BODY=""
OUTFILE=""
MAX_TIME="20"
CONNECT_TIMEOUT="5"
FOLLOW="1"
INSECURE="0"
SILENT="0"
SHOW_HEADERS="0"
HEAD_ONLY="0"

# headers array
declare -a HDRS=()

# First arg can be URL unless it starts with --
if [[ "${1:-}" != --* ]]; then
  URL="$1"
  shift
fi

if [[ -z "${URL}" ]]; then
  usage
  exit 2
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --method)
      METHOD="${2:-}"
      shift 2
      ;;
    --data)
      DATA="${2:-}"
      shift 2
      ;;
    --json)
      JSON_BODY="${2:-}"
      shift 2
      ;;
    --header)
      HDRS+=("$2")
      shift 2
      ;;
    --output)
      OUTFILE="${2:-}"
      shift 2
      ;;
    --max-time)
      MAX_TIME="${2:-}"
      shift 2
      ;;
    --connect-timeout)
      CONNECT_TIMEOUT="${2:-}"
      shift 2
      ;;
    --no-follow)
      FOLLOW="0"
      shift
      ;;
    --insecure)
      INSECURE="1"
      shift
      ;;
    --silent)
      SILENT="1"
      shift
      ;;
    --show-headers)
      SHOW_HEADERS="1"
      shift
      ;;
    --head)
      HEAD_ONLY="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

# Build curl args
declare -a CURL_ARGS=()

CURL_ARGS+=("--request" "${METHOD}")
CURL_ARGS+=("--max-time" "${MAX_TIME}")
CURL_ARGS+=("--connect-timeout" "${CONNECT_TIMEOUT}")
CURL_ARGS+=("--location") # follow redirects by default
if [[ "${FOLLOW}" == "0" ]]; then
  # remove --location by rebuilding without it
  CURL_ARGS=("--request" "${METHOD}" "--max-time" "${MAX_TIME}" "--connect-timeout" "${CONNECT_TIMEOUT}")
fi

# error handling & output control
# -sS: silent but show errors
if [[ "${SILENT}" == "1" ]]; then
  CURL_ARGS+=("-sS")
else
  CURL_ARGS+=("-S") # show errors (progress still shown)
fi

if [[ "${INSECURE}" == "1" ]]; then
  CURL_ARGS+=("--insecure")
fi

# HEAD mode
if [[ "${HEAD_ONLY}" == "1" ]]; then
  CURL_ARGS+=("--head")
fi

# Headers
for h in "${HDRS[@]}"; do
  CURL_ARGS+=("--header" "${h}")
done

# Body: JSON takes precedence over --data
if [[ -n "${JSON_BODY}" ]]; then
  CURL_ARGS+=("--header" "Content-Type: application/json")
  CURL_ARGS+=("--data-raw" "${JSON_BODY}")
elif [[ -n "${DATA}" ]]; then
  CURL_ARGS+=("--data-raw" "${DATA}")
fi

# Headers output
# If requested, dump response headers to stderr.
# Use -D - to print headers to stdout; we want stderr, so use a temp via process substitution if available.
# Portable approach: write to a temp file and cat to stderr.
HDR_TMP=""
cleanup() {
  [[ -n "${HDR_TMP}" && -f "${HDR_TMP}" ]] && rm -f "${HDR_TMP}"
}
trap cleanup EXIT

if [[ "${SHOW_HEADERS}" == "1" ]]; then
  HDR_TMP="$(mktemp)"
  CURL_ARGS+=("-D" "${HDR_TMP}")
fi

# Output file or stdout
if [[ -n "${OUTFILE}" ]]; then
  CURL_ARGS+=("--output" "${OUTFILE}")
fi

# Execute
set +e
curl "${CURL_ARGS[@]}" "${URL}"
RC=$?
set -e

if [[ "${SHOW_HEADERS}" == "1" && -f "${HDR_TMP}" ]]; then
  echo "----- response headers -----" >&2
  cat "${HDR_TMP}" >&2
  echo "----------------------------" >&2
fi

if [[ $RC -ne 0 ]]; then
  echo "error: curl exited with code ${RC}" >&2
  exit $RC
fi

exit 0