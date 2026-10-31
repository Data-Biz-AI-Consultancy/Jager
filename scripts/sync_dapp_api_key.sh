#!/usr/bin/env bash
# Sync DAPP_API_KEY from DAPP .env into Jager .env without printing the secret.
set -euo pipefail

DAPP_ENV="${1:-}"
JAGER_ENV="${2:-}"

if [[ -z "$DAPP_ENV" || -z "$JAGER_ENV" ]]; then
  echo "Usage: $0 <dapp.env> <jager.env>" >&2
  exit 2
fi
if [[ ! -f "$DAPP_ENV" ]]; then
  echo "ERROR: DAPP env not found: $DAPP_ENV" >&2
  exit 1
fi
if [[ ! -f "$JAGER_ENV" ]]; then
  echo "ERROR: Jager env not found: $JAGER_ENV" >&2
  exit 1
fi

# Extract value without echoing it (strip optional surrounding quotes)
raw="$(grep -E '^DAPP_API_KEY=' "$DAPP_ENV" | head -n1 | cut -d= -f2- || true)"
if [[ -z "$raw" ]]; then
  echo "ERROR: DAPP_API_KEY missing or empty in DAPP .env" >&2
  exit 1
fi
# Strip matching single/double quotes only
if [[ "$raw" =~ ^\".*\"$ ]]; then
  raw="${raw:1:${#raw}-2}"
elif [[ "$raw" =~ ^\'.*\'$ ]]; then
  raw="${raw:1:${#raw}-2}"
fi
if [[ -z "$raw" ]]; then
  echo "ERROR: DAPP_API_KEY empty after parsing" >&2
  exit 1
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

if grep -qE '^DAPP_API_KEY=' "$JAGER_ENV"; then
  # Replace existing line (empty or non-empty)
  awk -v val="$raw" '
    BEGIN { OFS="" }
    /^DAPP_API_KEY=/ {
      print "DAPP_API_KEY=", val
      replaced=1
      next
    }
    { print }
    END {
      if (!replaced) print "DAPP_API_KEY=" val
    }
  ' "$JAGER_ENV" > "$tmp"
  echo "Updated existing DAPP_API_KEY in Jager .env"
else
  # Append with trailing newline hygiene
  cp "$JAGER_ENV" "$tmp"
  # Ensure file ends with newline before append
  if [[ -s "$tmp" ]] && [[ "$(tail -c1 "$tmp" | wc -l)" -eq 0 ]]; then
    printf '\n' >> "$tmp"
  fi
  printf 'DAPP_API_KEY=%s\n' "$raw" >> "$tmp"
  echo "Appended DAPP_API_KEY to Jager .env"
fi

mv "$tmp" "$JAGER_ENV"
trap - EXIT

# Verify presence without printing value
if grep -qE '^DAPP_API_KEY=.+' "$JAGER_ENV"; then
  echo "OK: Jager .env DAPP_API_KEY is set (non-empty)"
else
  echo "ERROR: Jager .env DAPP_API_KEY still empty/missing" >&2
  exit 1
fi
