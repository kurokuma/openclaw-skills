---
name: curl
description: Fetch URL content using curl (Bash). Supports GET/POST, headers, timeouts, redirects, and optional output file.
---

# curl Fetch Skill

This skill fetches web content using `curl` from Bash.

## Usage

Provide a URL as input.

Examples:
- `bash fetch.sh https://example.com`
- `bash fetch.sh https://example.com --head`
- `bash fetch.sh https://example.com --max-time 20 --connect-timeout 5`
- `bash fetch.sh https://example.com --header "User-Agent: mybot" --header "Accept: text/html"`
- `bash fetch.sh https://example.com --output page.html`
- `bash fetch.sh https://httpbin.org/post --method POST --data 'a=1&b=2'`
- `bash fetch.sh https://httpbin.org/post --method POST --json '{"a":1}'`

## Requirements

- `bash`
- `curl`

## Scripts

- `fetch.sh`: Executes the curl request and prints the response body to stdout (or saves to file with `--output`).