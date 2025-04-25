#!/bin/bash
# Usage: LLM_GEMINI_KEY=... ./scrape.sh
datestring=$(date -u +"%Y-%m-%dT%H:%M:%S")
# make htmls and jsons directories if they don't exist
mkdir -p htmls
mkdir -p jsons
# get the html, and both
# - save to a file
# - pipe to the python script that parses to json
curl https://apfc.org/performance/ | tee "htmls/$datestring.html" | LLM_GEMINI_KEY=$LLM_GEMINI_KEY uv run parse.py > "jsons/$datestring.json"