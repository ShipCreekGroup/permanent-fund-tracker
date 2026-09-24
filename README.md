# AK Permanent Fund Scraper

We want to be able to see the historical trend of the
[Alaska Permanent Fund](https://en.wikipedia.org/wiki/Alaska_Permanent_Fund).
The current value is published daily at https://apfc.org/performance/,
but we haven't found a way to get daily values from the past.
The only historical data we can find is monthly summaries.
This doesn't have the needed granularity to capture some
rapid fluctuations, like are happening now, in April 2025.

Github suspended running the daily scraper in Dec 2025 due to inactivity in
this repository. I just noticed in Sep 2026, so there is a ~9 month
gap in data coverage in there.

We first store the raw HTML (about 206kb per page as of april 2025)
in the `htmls/` folder. This is so we have the raw source of truth
and can re-compute derived metrics later as needed.
We also run the HTML through an LLM to get structured data out,
that is stored in the `jsons/` folder.
We scrape once per day through github actions. The action runs hourly,
and skips if that (UTC) day already has a successful scrape, so transient
failures get retried the next hour.

The scrape saves APFC's category names exactly as they appear on the page.
APFC sometimes renames rows (eg "Stocks" became "Public Equities/Stocks"),
so `categories.json` lists the known categories and their other names, and
the chart uses it to keep each category as one series. After each scrape,
`check_categories.py` fails the GitHub Action if a category is unknown or
missing. The data is still saved. Fix it by updating `categories.json`.

The idea for this technique of "Git Scraping" comes from
[Simon Willison](https://simonwillison.net/series/git-scraping/).
