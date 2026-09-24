#!/bin/bash
# Usage: LLM_GEMINI_KEY=... ./scrape.sh
# Scrapes at most once per UTC day: exits without doing anything if today
# already has a json. Runs hourly in CI, so a failed scrape is retried the
# next hour.
set -euo pipefail

today=$(date -u +"%Y-%m-%d")
if compgen -G "jsons/${today}T*.json" > /dev/null; then
    echo "Already scraped today ($today), skipping."
    exit 0
fi

datestring=$(date -u +"%Y-%m-%dT%H:%M:%S")
mkdir -p htmls jsons
# Write to temp files and only move them into place once the whole
# fetch + parse succeeds, so a failure leaves nothing behind.
html_tmp=$(mktemp)
json_tmp=$(mktemp)
trap 'rm -f "$html_tmp" "$json_tmp"' EXIT

curl -fsSL https://apfc.org/performance/ > "$html_tmp"
LLM_GEMINI_KEY=$LLM_GEMINI_KEY uv run parse.py "$html_tmp" > "$json_tmp"

mv "$html_tmp" "htmls/$datestring.html"
mv "$json_tmp" "jsons/$datestring.json"

# Fail (after saving) if APFC's categories changed. The workflow still
# commits the data, and the failed run triggers GitHub's failure email.
uv run check_categories.py "jsons/$datestring.json"
