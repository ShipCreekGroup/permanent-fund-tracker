# /// script
# requires-python = ">=3.10"
# ///
"""Check that scraped data only has the portfolio categories we know about.

The scrape saves APFC's row labels as-is. categories.json lists the known
categories and other names APFC has used for them, and the chart uses it
to merge renamed rows. If APFC adds, removes, or renames a row, this
exits with an error so the GitHub Action fails and someone notices.

To fix a failure, edit categories.json:
- a rename: add the new name to "aliases", mapped to the existing category
- a genuinely new or removed category: update "categories"
Then re-run this on the file that failed to confirm the fix.

Usage:
    uv run check_categories.py jsons/2026-09-24T05:15:17.json [more.json ...]
"""

import json
import sys
from pathlib import Path

CONFIG = json.loads((Path(__file__).parent / "categories.json").read_text())
CATEGORIES: list[str] = CONFIG["categories"]
ALIASES: dict[str, str] = CONFIG["aliases"]


def problems(raw_names: list[str]) -> list[str]:
    """Descriptions of every unknown or missing category in `raw_names`."""
    names = [ALIASES.get(n, n) for n in raw_names]
    unknown = [raw for raw, n in zip(raw_names, names) if n not in CATEGORIES]
    missing = [c for c in CATEGORIES if c not in names]
    return [f"unknown category {n!r}" for n in unknown] + [
        f"missing category {c!r}" for c in missing
    ]


def main(paths: list[str]) -> int:
    failed = False
    for path in paths:
        names = [name for name, _amount in json.loads(Path(path).read_text())["lineitems"]]
        for problem in problems(names):
            print(f"{path}: {problem}", file=sys.stderr)
            failed = True
    if failed:
        print(
            "APFC's list of categories changed. The data was still saved. "
            "See check_categories.py for how to fix this.",
            file=sys.stderr,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
